"""
Phase 2 - invoices table (table 3 of 3, completes Phase 2). One row per
Stripe invoice issued against a subscription: the initial charge at
trial-conversion/resubscribe, one per successful renewal, plus a failed
invoice for the small populations that are currently `past_due` or that
churned `involuntary`ly right at a renewal boundary.

No trial-only subscription (interval_id 0 in build_subscription_objects --
trial_in_progress / canceled_during_trial / expired_passively) ever gets an
invoice: nothing is ever charged during a trial in this design, so there's
nothing to invoice. Only subscriptions with interval_id >= 1 (a real,
successfully-started paid interval) produce invoices.

Built on top of subscription_events.csv's already-validated `renewed` events
(reused directly, not recomputed) plus build_subscription_objects() for the
subscription-level fields -- single source of truth for both.

Handles the one genuine subtlety in the mapping: 32 subscriptions have a
single upgraded/downgraded tier change mid-life (see subscription_events.csv).
Invoices issued before that change date bill the OLD tier's price; invoices
on/after it bill the NEW tier's price -- a plan_id that reflects only the
subscription's FINAL tier (as subscriptions.csv correctly does) would silently
overcharge/undercharge every pre-change invoice for those 32 subscriptions, so
invoices.csv gets its own plan_id per row rather than inheriting one from
subscriptions.csv.

Two failure-invoice cases, each gated on a real precondition (not assumed):
  - `uncollectible`: only for `involuntary` churns where canceled_at exactly
    coincides with a real renewal-cycle boundary. For annual-billed
    subscriptions that churn early (well before their first 12-month
    renewal), the cancellation isn't tied to any billing event at all
    (more like a chargeback/compliance termination) -- no invoice is invented
    for those, since Stripe wouldn't generate one either.
  - `open`: for every currently `past_due` subscription, covering the
    current (unpaid) period -- reuses current_period_start/end exactly.

Output: data/invoices.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED
import build_subscriptions as bs


def build_invoices(seed=SEED + 9):
    rng = np.random.default_rng(seed)
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    objects = bs.build_subscription_objects(timeline)
    plans = pd.read_csv("../data/subscription_plans.csv").set_index("plan_id")

    events = pd.read_csv("../data/subscription_events.csv")
    # Dedupe the deliberate webhook-style duplicates before using events as
    # source data -- a duplicated "renewed" webhook must not produce two invoices.
    events = events.drop_duplicates(subset=["subscription_id", "event_type", "event_at"])
    events["event_at"] = pd.to_datetime(events["event_at"])

    renewed_by_sub = events[events["event_type"] == "renewed"].groupby("subscription_id")["event_at"].apply(
        lambda s: sorted(d.date() for d in s))
    change_by_sub = {
        row.subscription_id: (row.event_at.date(), row.old_plan, row.new_plan)
        for row in events[events["event_type"].isin(["upgraded", "downgraded"])].itertuples()
    }

    def price_of(plan_id):
        return float(plans.loc[plan_id, "price"])

    rows = []

    for obj in objects:
        if obj["interval_id"] == 0:
            continue  # trial never converted -- nothing was ever charged

        sub_id, cid, billing_interval = obj["subscription_id"], obj["customer_id"], obj["billing_interval"]
        origin = obj["trial_end"] if obj["interval_id"] == 1 else obj["start_date"]
        change = change_by_sub.get(sub_id)  # (date, old_plan_id, new_plan_id) or None

        def plan_id_at(d, _change=change, _final_tier_plan=obj["plan_id"]):
            if _change is None:
                return _final_tier_plan
            change_date, old_plan, new_plan = _change
            return old_plan if d < change_date else new_plan

        # period_end for each invoice must be computed the SAME way
        # subscriptions.py computes period boundaries -- directly from origin
        # at each cycle's own index k, never by chaining +1 month off the
        # previous invoice's date. relativedelta month-end clamping (e.g. Jan
        # 30 -> Feb 28 -> Mar 28, NOT Mar 30) makes chaining silently drift
        # away from the direct-from-origin dates current_period_start/end
        # already use, breaking period contiguity between invoices.
        invoice_dates = [origin] + list(renewed_by_sub.get(sub_id, []))
        n_renewals = len(invoice_dates) - 1  # number of successful renewals so far
        for i, d in enumerate(invoice_dates):
            plan_id = plan_id_at(d)
            rows.append({
                "subscription_id": sub_id, "customer_id": cid, "plan_id": plan_id,
                "amount_due": price_of(plan_id), "currency": "usd",
                "period_start": d, "period_end": bs._advance(origin, billing_interval, i + 1),
                "status": "paid",
                "paid_at": d + datetime.timedelta(hours=int(rng.integers(0, 20))),
            })

        if obj["cancel_reason"] == "involuntary":
            # Direct-from-origin, matching how current_period_start/end were
            # derived -- NOT bs._advance(obj["current_period_start"], ..., 1),
            # which chains off an already-clamped date and can drift.
            next_boundary = bs._advance(origin, billing_interval, n_renewals + 1)
            if next_boundary == obj["canceled_at"]:
                d = obj["canceled_at"]
                plan_id = plan_id_at(d)
                rows.append({
                    "subscription_id": sub_id, "customer_id": cid, "plan_id": plan_id,
                    "amount_due": price_of(plan_id), "currency": "usd",
                    "period_start": d, "period_end": bs._advance(origin, billing_interval, n_renewals + 2),
                    "status": "uncollectible", "paid_at": None,
                })

        if obj["status"] == "past_due":
            d = obj["current_period_start"]
            plan_id = plan_id_at(d)
            rows.append({
                "subscription_id": sub_id, "customer_id": cid, "plan_id": plan_id,
                "amount_due": price_of(plan_id), "currency": "usd",
                "period_start": obj["current_period_start"], "period_end": obj["current_period_end"],
                "status": "open", "paid_at": None,
            })

    df = pd.DataFrame(rows)
    df["period_start"] = pd.to_datetime(df["period_start"])
    df = df.sort_values(["customer_id", "period_start"]).reset_index(drop=True)
    df.insert(0, "invoice_id", [f"inv_{i+1:06d}" for i in range(len(df))])

    seconds = rng.integers(0, 86400, size=len(df))
    df["created_at"] = (df["period_start"] + pd.to_timedelta(seconds, unit="s")).dt.strftime("%Y-%m-%dT%H:%M:%S")
    df["period_start"] = df["period_start"].dt.strftime("%Y-%m-%d")
    df["period_end"] = pd.to_datetime(df["period_end"]).dt.strftime("%Y-%m-%d")
    df["paid_at"] = pd.to_datetime(df["paid_at"]).dt.strftime("%Y-%m-%dT%H:%M:%S")

    return df[["invoice_id", "subscription_id", "customer_id", "plan_id", "amount_due", "currency",
               "period_start", "period_end", "status", "paid_at", "created_at"]]


if __name__ == "__main__":
    df = build_invoices()
    df.to_csv("../data/invoices.csv", index=False)
    print(f"Wrote {len(df)} invoices\n")
    print(df["status"].value_counts().to_string())
    print(f"\nTotal paid revenue: ${df.loc[df['status']=='paid','amount_due'].sum():,.2f}")
