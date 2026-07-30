"""
Phase 2 - subscriptions table (Stripe-shaped, table 1 of 3: subscriptions,
subscription_events, invoices). Fully separate from storefront commerce
(orders/payments live in Phase 3).

One row per Stripe *Subscription object*, not one row per customer. A
customer's full subscription history in the master timeline is a sequence of
`subscription_intervals` (continuous non-lapsed spans) plus a leading trial.
Mapped to Stripe-realistic subscription objects:
  - The trial + its first interval (if the trial converts) are the SAME
    Stripe subscription object -- Stripe subscriptions start `trialing` and
    move to `active` on conversion, they don't get a new ID. This also
    covers trials that never convert (canceled_during_trial /
    expired_passively / still trial_in_progress as of END_DATE): still one
    subscription object each, just one that never leaves `trialing` or that
    lands straight in `canceled`.
  - Every subsequent interval (a win-back reactivation after a full
    cancellation) is a NEW subscription object -- a real resubscribe in
    Stripe terms, created straight into `active` with no trial.

This resolves the long-flagged "billing_interval isn't in the master
timeline" gap (generation_plan.md's Cross-phase consistency commitments,
item 1): neither billing_interval (monthly/annual) nor a specific plan tier
for never-converted trials exist in Phase 0 at all, so both are assigned
here, once per subscription object, using this script's own seeded rng.
`current_period_start`/`current_period_end` are computed from that
billing_interval by cycling forward from the object's start date -- for any
currently open (active/past_due) subscription, this guarantees
current_period_end lands AFTER END_DATE (a real, still-in-the-future
renewal date), which is exactly the "renewal approaching" signal the
`segments` table's "High Churn Risk" segment has been waiting on.

Two more small mechanics layered on at this phase (also not in the master
timeline, since Phase 0 doesn't model billing-object-level detail):
  - `past_due`: a Stripe dunning/grace-period status -- a renewal payment
    attempt just failed but the subscription hasn't been canceled (yet).
    Applied to a small share of subscriptions that renewed very recently
    (see PAST_DUE_RATE / PAST_DUE_WINDOW_DAYS in params.py). `past_due_since`
    records exactly when that failed attempt happened -- added (2026-07-30,
    same day as the initial build) once `subscription_events` needed a
    single source of truth for the matching unresolved payment_failed event,
    rather than letting the two tables each invent their own date.
  - `paused` is a valid Stripe status (and listed in schema_reference.md's
    enum) but is NOT modeled/populated here -- 0 rows will have this status.
    Flagged explicitly rather than silently omitted; easy to add later if
    wanted (Stripe's pause_collection feature, not currently in scope).

Output: data/subscriptions.csv
"""
import datetime
import json
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from params import SEED, END_DATE, TRIAL_DAYS, BASIC_PLAN_SHARE, ANNUAL_BILLING_SHARE, \
    PAST_DUE_RATE, PAST_DUE_WINDOW_DAYS
from build_customers import customer_id_for


def _advance(date, billing_interval, n):
    return date + (relativedelta(months=n) if billing_interval == "month" else relativedelta(years=n))


def _current_period(origin, billing_interval, as_of_date):
    """The (start, end) of the billing cycle -- counted forward from `origin`
    in steps of `billing_interval` -- that contains `as_of_date`."""
    n = 0
    while _advance(origin, billing_interval, n + 1) <= as_of_date:
        n += 1
    return _advance(origin, billing_interval, n), _advance(origin, billing_interval, n + 1)


def _plan_id(tier, billing_interval):
    return f"plan_{tier}_{'monthly' if billing_interval == 'month' else 'annual'}"


def build_subscription_objects(timeline, seed=SEED + 7):
    """Returns one dict per Stripe-shaped subscription object, INCLUDING
    internal linkage fields (sim_customer_id, interval_id) that later
    builders (subscription_events) need to attach raw timeline events to the
    right subscription_id -- kept as the single source of truth so the two
    tables can never drift apart on this mapping. interval_id is 0 for a
    trial that never converted (no real interval exists), otherwise it's the
    timeline's own interval_id (1 = the trial-converted interval, 2+ =
    win-back resubscribes)."""
    rng = np.random.default_rng(seed)
    objects = []
    sub_num = 0

    for t in timeline:
        trial = t["trial"]
        if trial is None:
            continue

        sim_id = t["customer_id"]
        customer_id = customer_id_for(sim_id)
        trial_start = datetime.date.fromisoformat(trial["start"])
        trial_end = datetime.date.fromisoformat(trial["end"])
        intervals = t["subscription_intervals"]

        # --- Subscription object #1: the trial itself (+ interval 1 if converted) ---
        sub_num += 1
        billing_interval = str(rng.choice(["month", "year"], p=[1 - ANNUAL_BILLING_SHARE, ANNUAL_BILLING_SHARE]))

        if trial["outcome"] == "trial_in_progress":
            tier = str(rng.choice(["basic", "plus"], p=[BASIC_PLAN_SHARE, 1 - BASIC_PLAN_SHARE]))
            objects.append({
                "subscription_id": f"sub_{sub_num:05d}", "sim_customer_id": sim_id,
                "customer_id": customer_id, "interval_id": 0,
                "plan_id": _plan_id(tier, billing_interval), "billing_interval": billing_interval,
                "status": "trialing", "trial_start": trial_start, "trial_end": trial_end,
                "start_date": trial_start, "current_period_start": trial_start, "current_period_end": trial_end,
                "canceled_at": None, "cancel_reason": None,
            })
        elif trial["outcome"] == "canceled_during_trial":
            # Distinct from a real post-conversion "voluntary" churn -- this is a
            # trial cancellation, never involves a real payment, and is always
            # voluntary by definition (no such thing as an "involuntary" trial
            # cancellation). Keeping it as its own reason value (rather than
            # reusing "voluntary") keeps the real INVOLUNTARY_CHURN_SHARE-driven
            # voluntary/involuntary split (which only applies to real,
            # post-conversion churns) from getting diluted by this much larger,
            # mechanically unrelated population.
            tier = str(rng.choice(["basic", "plus"], p=[BASIC_PLAN_SHARE, 1 - BASIC_PLAN_SHARE]))
            canceled_at = trial_start + datetime.timedelta(days=int(rng.integers(1, TRIAL_DAYS)))
            objects.append({
                "subscription_id": f"sub_{sub_num:05d}", "sim_customer_id": sim_id,
                "customer_id": customer_id, "interval_id": 0,
                "plan_id": _plan_id(tier, billing_interval), "billing_interval": billing_interval,
                "status": "canceled", "trial_start": trial_start, "trial_end": trial_end,
                "start_date": trial_start, "current_period_start": trial_start, "current_period_end": canceled_at,
                "canceled_at": canceled_at, "cancel_reason": "trial_canceled",
            })
        elif trial["outcome"] == "expired_passively":
            tier = str(rng.choice(["basic", "plus"], p=[BASIC_PLAN_SHARE, 1 - BASIC_PLAN_SHARE]))
            objects.append({
                "subscription_id": f"sub_{sub_num:05d}", "sim_customer_id": sim_id,
                "customer_id": customer_id, "interval_id": 0,
                "plan_id": _plan_id(tier, billing_interval), "billing_interval": billing_interval,
                "status": "canceled", "trial_start": trial_start, "trial_end": trial_end,
                "start_date": trial_start, "current_period_start": trial_start, "current_period_end": trial_end,
                "canceled_at": trial_end, "cancel_reason": "trial_expired",
            })
        else:  # converted -- combine trial + interval 1
            iv = intervals[0]
            tier = iv["plan"]
            origin = trial_end
            if iv["end"] is None:
                current_period_start, current_period_end = _current_period(origin, billing_interval, END_DATE)
                status, canceled_at, cancel_reason = "active", None, None
            else:
                ended_at = datetime.date.fromisoformat(iv["end"])
                current_period_start, _ = _current_period(origin, billing_interval, ended_at - datetime.timedelta(days=1))
                current_period_end = ended_at
                status = "canceled"
                canceled_at = ended_at
                cancel_reason = iv["end_reason"]
            objects.append({
                "subscription_id": f"sub_{sub_num:05d}", "sim_customer_id": sim_id,
                "customer_id": customer_id, "interval_id": 1,
                "plan_id": _plan_id(tier, billing_interval), "billing_interval": billing_interval,
                "status": status, "trial_start": trial_start, "trial_end": trial_end,
                "start_date": trial_end, "current_period_start": current_period_start,
                "current_period_end": current_period_end,
                "canceled_at": canceled_at, "cancel_reason": cancel_reason,
            })

        # --- Subsequent subscription objects: win-back resubscribes (interval_id 2+) ---
        for iv in intervals[1:]:
            sub_num += 1
            billing_interval = str(rng.choice(["month", "year"], p=[1 - ANNUAL_BILLING_SHARE, ANNUAL_BILLING_SHARE]))
            tier = iv["plan"]
            origin = datetime.date.fromisoformat(iv["start"])
            if iv["end"] is None:
                current_period_start, current_period_end = _current_period(origin, billing_interval, END_DATE)
                status, canceled_at, cancel_reason = "active", None, None
            else:
                ended_at = datetime.date.fromisoformat(iv["end"])
                current_period_start, _ = _current_period(origin, billing_interval, ended_at - datetime.timedelta(days=1))
                current_period_end = ended_at
                status = "canceled"
                canceled_at = ended_at
                cancel_reason = iv["end_reason"]
            objects.append({
                "subscription_id": f"sub_{sub_num:05d}", "sim_customer_id": sim_id,
                "customer_id": customer_id, "interval_id": iv["interval_id"],
                "plan_id": _plan_id(tier, billing_interval), "billing_interval": billing_interval,
                "status": status, "trial_start": None, "trial_end": None,
                "start_date": origin, "current_period_start": current_period_start,
                "current_period_end": current_period_end,
                "canceled_at": canceled_at, "cancel_reason": cancel_reason,
            })

    # --- past_due overlay: a small share of just-renewed active subscriptions ---
    # are currently in a payment-failure grace period rather than cleanly active.
    # past_due_since records exactly when that renewal payment attempt failed --
    # needed by subscription_events (Phase 2, table 2) to log the matching
    # unresolved payment_failed event, so the two tables can't drift apart on
    # "why is this subscription past_due."
    for obj in objects:
        obj["past_due_since"] = None
        if obj["status"] == "active" and (END_DATE - obj["current_period_start"]).days <= PAST_DUE_WINDOW_DAYS:
            if rng.random() < PAST_DUE_RATE:
                obj["status"] = "past_due"
                days_since_renewal = (END_DATE - obj["current_period_start"]).days
                offset = int(rng.integers(0, max(1, days_since_renewal + 1)))
                obj["past_due_since"] = obj["current_period_start"] + datetime.timedelta(days=offset)

    return objects


def build_subscriptions():
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    objects = build_subscription_objects(timeline)

    rng = np.random.default_rng(SEED + 7 + 1)  # separate stream, just for created_at time-of-day
    rows = []
    for obj in objects:
        seconds = int(rng.integers(0, 86400))
        created_at = datetime.datetime.combine(obj["start_date"], datetime.time()) + datetime.timedelta(seconds=seconds)
        rows.append({
            "subscription_id": obj["subscription_id"],
            "customer_id": obj["customer_id"],
            "plan_id": obj["plan_id"],
            "billing_interval": obj["billing_interval"],
            "status": obj["status"],
            "trial_start": obj["trial_start"].isoformat() if obj["trial_start"] else None,
            "trial_end": obj["trial_end"].isoformat() if obj["trial_end"] else None,
            "start_date": obj["start_date"].isoformat(),
            "current_period_start": obj["current_period_start"].isoformat(),
            "current_period_end": obj["current_period_end"].isoformat(),
            "canceled_at": obj["canceled_at"].isoformat() if obj["canceled_at"] else None,
            "cancel_reason": obj["cancel_reason"],
            "past_due_since": obj["past_due_since"].isoformat() if obj["past_due_since"] else None,
            "created_at": created_at.isoformat(),
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_subscriptions()
    df.to_csv("../data/subscriptions.csv", index=False)
    print(f"Wrote {len(df)} subscriptions\n")
    print(df["status"].value_counts().to_string())
    print(f"\nbilling_interval split:\n{df['billing_interval'].value_counts(normalize=True).to_string()}")
    print(f"\ncancel_reason split (canceled only):\n{df.loc[df['status']=='canceled','cancel_reason'].value_counts().to_string()}")
