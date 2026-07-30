"""
Phase 0 - Steps 5 & 6: Per-customer master timeline + attribution ground truth.

For each of the N_CUSTOMERS customers, simulates their whole lifecycle as one
ground-truth object: signup, trial, subscription intervals (with churn/win-back),
and order events -- respecting the rule that course purchases never fall inside an
active subscription interval. Every real table built in later phases derives from
this.

Churn model: two subscriber segments (see params.py for the math). "Loyal"
subscribers essentially never organically churn within the dataset window;
"quick" subscribers churn fast (mean ~3 months). Blended, this hits ~40% annual
retention while realized churns land at ~3 months average tenure -- a single
constant churn rate can't satisfy both at once.

Output:
  internal/_sim_customer_timeline.json          (full nested ground truth)
  internal/_sim_customer_timeline_summary.csv   (flattened overview)
  internal/_sim_attribution_ground_truth.json   (true acquisition/reactivation channel)
"""
import datetime
import hashlib
import json
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from params import (
    SEED, N_CUSTOMERS, START_DATE, END_DATE, TRIAL_DAYS,
    EVER_SUBSCRIBE_RATE, TRIAL_CONVERSION_RATE, TRIAL_CANCEL_RATE, BASIC_PLAN_SHARE,
    LOYAL_SEGMENT_SHARE, QUICK_CHURN_MEAN_TENURE_MONTHS,
    PLAN_CHANGE_PROBABILITY, INVOLUNTARY_CHURN_SHARE,
    WINBACK_PROBABILITY, WINBACK_MIN_GAP_MONTHS, PAYMENT_BLIP_PROBS,
    REACTIVATION_CHANNEL_WEIGHTS, LAPSED_STILL_BUYING_RATE,
    MERCH_TO_SUB_EMAIL_RATE, MERCH_TO_SUB_TRIAL_CONVERSION_RATE,
    MERCH_TO_SUB_TRIGGER_GAP_MONTHS_RANGE, MONTHLY_SEASONALITY,
    COURSE_ORDERS_PER_YEAR_NONSUB_RANGE,
    MERCH_ORDERS_PER_YEAR_RANGE, COURSE_PRICE_TIERS, COURSE_PRICE_WEIGHTS,
    MERCH_PRICE_TIERS, MERCH_PRICE_WEIGHTS, SUBSCRIBER_MERCH_DISCOUNT,
)
from sim_utils import (
    load_calendar, load_channel_mix, sample_weighted_date, sample_channel,
    sample_seasonal_month_date,
)


def _resolved_payment_blips(rng, cursor, span_end):
    """Resolved payment-failure blips: noise events that don't end the subscription."""
    events = []
    n_blips = int(rng.choice(list(PAYMENT_BLIP_PROBS.keys()), p=list(PAYMENT_BLIP_PROBS.values())))
    span_days = max(1, (span_end - cursor).days)
    for _ in range(n_blips):
        offset_days = int(rng.integers(0, span_days))
        blip_date = cursor + datetime.timedelta(days=offset_days)
        if blip_date < span_end:
            events.append({"event_type": "payment_failed", "event_at": blip_date.isoformat(),
                            "resolved": True})
    return events


def simulate_subscription_lifecycle(rng, start_date, initial_plan, dataset_end):
    """Simulate a converted subscriber's full interval history from trial-end
    forward, using the two-segment churn model. Returns (intervals, events,
    churn_date, reactivation_channels, segment).

    Win-back timing is sampled by calendar MONTH ONLY (MONTHLY_SEASONALITY),
    restricted to start at least WINBACK_MIN_GAP_MONTHS after churn -- this
    concentrates reactivations around January every year rather than spreading
    them uniformly or (as an earlier attempt did) biasing toward whatever month
    happens to be closest to the dataset's end date."""
    intervals, events, reactivation_channels = [], [], []
    cursor = start_date
    interval_num = 0
    churn_date = None

    segment = "loyal" if rng.random() < LOYAL_SEGMENT_SHARE else "quick"

    while cursor < dataset_end:
        interval_num += 1
        plan = initial_plan if interval_num == 1 else str(rng.choice(["basic", "plus"], p=[0.75, 0.25]))

        if segment == "loyal":
            # Runs to the end of the dataset -- does not organically churn, though
            # it can still show resolved payment-failure noise and a plan change.
            events.extend(e | {"interval_id": interval_num} for e in _resolved_payment_blips(rng, cursor, dataset_end))
            if rng.random() < PLAN_CHANGE_PROBABILITY:
                span_days = max(1, (dataset_end - cursor).days)
                change_date = cursor + datetime.timedelta(days=int(rng.integers(30, max(31, span_days))))
                if change_date < dataset_end:
                    new_plan = "plus" if plan == "basic" else "basic"
                    events.append({"event_type": "upgraded" if new_plan == "plus" else "downgraded",
                                    "event_at": change_date.isoformat(), "interval_id": interval_num})
                    plan = new_plan
            intervals.append({"interval_id": interval_num, "plan": plan,
                               "start": cursor.isoformat(), "end": None, "end_reason": "ongoing"})
            churn_date = None
            break  # loyal subscribers don't cycle further

        # --- quick-churn segment ---
        tenure_months = max(1, int(round(rng.exponential(QUICK_CHURN_MEAN_TENURE_MONTHS))))
        tentative_end = cursor + relativedelta(months=tenure_months)

        events.extend(e | {"interval_id": interval_num}
                      for e in _resolved_payment_blips(rng, cursor, min(tentative_end, dataset_end)))

        if rng.random() < PLAN_CHANGE_PROBABILITY and tentative_end < dataset_end:
            change_offset = int(rng.integers(1, max(2, tenure_months)))
            change_date = cursor + relativedelta(months=change_offset)
            new_plan = "plus" if plan == "basic" else "basic"
            events.append({"event_type": "upgraded" if new_plan == "plus" else "downgraded",
                            "event_at": change_date.isoformat(), "interval_id": interval_num})
            plan = new_plan

        if tentative_end >= dataset_end:
            # Hasn't reached their (short) churn draw before the dataset ends -- rare,
            # only for very recent signups, but still possible.
            intervals.append({"interval_id": interval_num, "plan": plan,
                               "start": cursor.isoformat(), "end": None, "end_reason": "ongoing"})
            churn_date = None
            break

        end_reason = "involuntary" if rng.random() < INVOLUNTARY_CHURN_SHARE else "voluntary"
        if end_reason == "involuntary":
            events.append({"event_type": "payment_failed", "event_at": tentative_end.isoformat(),
                            "interval_id": interval_num, "resolved": False})
        events.append({"event_type": "canceled", "event_at": tentative_end.isoformat(),
                        "interval_id": interval_num, "reason": end_reason})
        intervals.append({"interval_id": interval_num, "plan": plan,
                           "start": cursor.isoformat(), "end": tentative_end.isoformat(), "end_reason": end_reason})
        churn_date = tentative_end.isoformat()

        if rng.random() < WINBACK_PROBABILITY:
            earliest_winback = tentative_end + relativedelta(months=WINBACK_MIN_GAP_MONTHS)
            if earliest_winback >= dataset_end:
                break
            next_start = sample_seasonal_month_date(rng, earliest_winback, dataset_end, MONTHLY_SEASONALITY)
            channel = str(rng.choice(list(REACTIVATION_CHANNEL_WEIGHTS.keys()),
                                      p=list(REACTIVATION_CHANNEL_WEIGHTS.values())))
            reactivation_channels.append({"interval_id": interval_num + 1, "channel": channel,
                                           "reactivated_at": next_start.isoformat()})
            events.append({"event_type": "resumed", "event_at": next_start.isoformat(),
                           "interval_id": interval_num + 1})
            cursor = next_start
            initial_plan = plan  # carry the plan forward; segment stays "quick"
        else:
            break

    return intervals, events, churn_date, reactivation_channels, segment


def active_subscription_windows(intervals):
    """Return list of (start, end) date tuples for active subscription coverage,
    used to keep course orders out of subscribed periods."""
    windows = []
    for iv in intervals:
        start = datetime.date.fromisoformat(iv["start"])
        end = datetime.date.fromisoformat(iv["end"]) if iv["end"] else END_DATE
        windows.append((start, end))
    return windows


def is_covered(date, windows):
    return any(start <= date <= end for start, end in windows)


def _reconcile_orders_with_subscription_windows(orders, sub_windows):
    """For the course_merch_only -> email-reactivation-conversion pathway,
    a customer's ORIGINAL organic order history is generated before we even
    know whether (or when) the email trigger will convert them -- so it's
    generated with sub_windows=[] (see the caller). If it later DOES convert,
    some of those pre-existing orders can retroactively fall inside the new
    subscription window, which is now known. Two real problems that causes,
    fixed here as a post-hoc reconciliation once sub_windows is finally known:
    1. A pre-existing COURSE order landing inside the subscription window is
       a hard business-rule violation (no course purchase during an active
       subscription) -- dropped entirely.
    2. A pre-existing MERCH order landing inside the window was drawn at
       full (non-subscriber) price, since it didn't know a subscription
       would exist yet -- retroactively flagged subscriber_discount_applied
       and re-priced at the standard 20% discount, so pricing matches what
       a real subscriber checkout would have shown.
    Found via Phase 3's `orders` table validation cross-checking against
    Phase 2's real `subscriptions.csv` -- the master timeline had never been
    checked against actual subscription windows for this specific pathway."""
    reconciled = []
    for o in orders:
        date = datetime.date.fromisoformat(o["date"])
        if o["order_type"] == "course" and is_covered(date, sub_windows):
            continue  # drop -- would be an impossible course-during-subscription order
        if o["order_type"] == "merch" and is_covered(date, sub_windows) and not o.get("subscriber_discount_applied", False):
            o = dict(o)
            o["amount"] = round(o["amount"] * (1 - SUBSCRIBER_MERCH_DISCOUNT), 2)
            o["subscriber_discount_applied"] = True
        reconciled.append(o)
    return reconciled


def _draw_order(rng, order_type, discounted=False):
    if order_type == "course":
        price = round(float(rng.choice(COURSE_PRICE_TIERS, p=COURSE_PRICE_WEIGHTS)), 2)
    else:
        price = round(float(rng.choice(MERCH_PRICE_TIERS, p=MERCH_PRICE_WEIGHTS)), 2)
        if discounted:
            price = round(price * (1 - SUBSCRIBER_MERCH_DISCOUNT), 2)
    return price


def generate_orders(rng, customer_start, dataset_end, account_type, sub_windows, churn_date):
    """Generate course + merch order events. Course orders never fall inside an
    active subscription window. For lapsed subscribers, post-lapse purchasing is
    explicitly gated by LAPSED_STILL_BUYING_RATE -- 90% go completely quiet after
    their most recent churn; the rest keep buying occasionally."""
    orders = []

    if account_type == "course_merch_only":
        active_years = max(0.25, (dataset_end - customer_start).days / 365.25)
        n_courses = min(int(rng.integers(*COURSE_ORDERS_PER_YEAR_NONSUB_RANGE)) * max(1, round(active_years)), 8)
        attempts, placed = 0, 0
        while placed < n_courses and attempts < max(1, n_courses) * 6:
            attempts += 1
            candidate = customer_start + datetime.timedelta(
                days=int(rng.integers(0, max(1, (dataset_end - customer_start).days))))
            if not is_covered(candidate, sub_windows):
                orders.append({"order_type": "course", "date": candidate.isoformat(),
                                "amount": _draw_order(rng, "course")})
                placed += 1

        n_merch = min(int(rng.integers(*MERCH_ORDERS_PER_YEAR_RANGE) * max(1, round(active_years))), 10)
        for _ in range(n_merch):
            span = max(1, (dataset_end - customer_start).days)
            candidate = customer_start + datetime.timedelta(days=int(rng.integers(0, span)))
            orders.append({"order_type": "merch", "date": candidate.isoformat(),
                            "amount": _draw_order(rng, "merch"), "subscriber_discount_applied": False})
        orders.sort(key=lambda o: o["date"])
        return orders

    # account_type == "subscriber": engaged window runs from signup to their most
    # recent churn (if lapsed) or to dataset_end (if still active).
    engaged_end = datetime.date.fromisoformat(churn_date) if churn_date else dataset_end
    engaged_days = max(1, (engaged_end - customer_start).days)
    engaged_years = max(0.25, engaged_days / 365.25)

    # Merch during the engaged window -- discount applied if covered by a sub window
    n_merch = min(int(rng.integers(*MERCH_ORDERS_PER_YEAR_RANGE) * max(1, round(engaged_years))), 10)
    for _ in range(n_merch):
        candidate = customer_start + datetime.timedelta(days=int(rng.integers(0, engaged_days)))
        discounted = is_covered(candidate, sub_windows)
        orders.append({"order_type": "merch", "date": candidate.isoformat(),
                        "amount": _draw_order(rng, "merch", discounted),
                        "subscriber_discount_applied": discounted})

    # Rare course purchase in a gap before their first trial or between intervals
    gap_days = sum((min(w[0], engaged_end) - customer_start).days for w in sub_windows if w[0] > customer_start)
    if sub_windows and rng.random() < 0.15 and gap_days > 14:
        pre_trial_end = sub_windows[0][0]
        candidate_span = (pre_trial_end - customer_start).days
        if candidate_span > 0:
            candidate = customer_start + datetime.timedelta(days=int(rng.integers(0, candidate_span)))
            orders.append({"order_type": "course", "date": candidate.isoformat(),
                            "amount": _draw_order(rng, "course")})

    # Post-lapse behavior: only relevant if currently lapsed (not just churned-then-rejoined)
    if churn_date is not None:
        post_lapse_days = (dataset_end - engaged_end).days
        if post_lapse_days > 0 and rng.random() < LAPSED_STILL_BUYING_RATE:
            n_post = int(rng.integers(1, 4))
            for _ in range(n_post):
                candidate = engaged_end + datetime.timedelta(days=int(rng.integers(0, post_lapse_days)))
                order_type = "course" if rng.random() < 0.5 else "merch"
                order = {"order_type": order_type, "date": candidate.isoformat(),
                         "amount": _draw_order(rng, order_type)}
                if order_type == "merch":
                    order["subscriber_discount_applied"] = False  # not subscribed anymore
                orders.append(order)
        # else: 90% case -- no purchases at all after their most recent churn

    orders.sort(key=lambda o: o["date"])
    return orders


def maybe_trigger_merch_to_sub_email(rng, orders, dataset_end):
    """For course/merch-only customers: sometimes a targeted "come try a
    membership" email, based on their own purchase history, lands and triggers
    a trial. Returns a trial dict (with trigger="email_reactivation") or None
    if the email never reaches them, or there isn't enough runway left in the
    dataset window to resolve a trial that starts this late."""
    if not orders:
        return None
    if rng.random() >= MERCH_TO_SUB_EMAIL_RATE:
        return None

    first_order_date = datetime.date.fromisoformat(min(o["date"] for o in orders))
    gap_months = int(rng.integers(MERCH_TO_SUB_TRIGGER_GAP_MONTHS_RANGE[0],
                                   MERCH_TO_SUB_TRIGGER_GAP_MONTHS_RANGE[1] + 1))
    trigger_date = first_order_date + relativedelta(months=gap_months)
    trial_end = trigger_date + datetime.timedelta(days=TRIAL_DAYS)
    if trigger_date >= dataset_end or trial_end >= dataset_end:
        return None  # not enough purchase history + runway left to resolve this yet

    roll = rng.random()
    if roll < MERCH_TO_SUB_TRIAL_CONVERSION_RATE:
        outcome = "converted"
    elif roll < MERCH_TO_SUB_TRIAL_CONVERSION_RATE + TRIAL_CANCEL_RATE:
        outcome = "canceled_during_trial"
    else:
        outcome = "expired_passively"

    return {"start": trigger_date.isoformat(), "end": trial_end.isoformat(),
            "outcome": outcome, "trigger": "email_reactivation"}


def assign_engagement_tier(rng, ever_converted, churn_date):
    """Tier reflects true subscription history (ever converted + currently
    active vs. lapsed), not the customer's original signup account_type --
    this also covers customers who converted later via the email-reactivation
    pathway, who should be tiered the same as any other subscriber."""
    if ever_converted and churn_date is None:
        return str(rng.choice(["power", "regular"], p=[0.6, 0.4]))
    if ever_converted and churn_date is not None:
        return str(rng.choice(["regular", "casual"], p=[0.5, 0.5]))
    return str(rng.choice(["casual", "regular"], p=[0.7, 0.3]))


def simulate_all_customers(seed=SEED + 2):
    rng = np.random.default_rng(seed)
    calendar = load_calendar()
    channel_mix = load_channel_mix()

    timelines = []
    attribution = []

    for customer_id in range(1, N_CUSTOMERS + 1):
        signup_date = sample_weighted_date(calendar, rng, start_date=START_DATE, end_date=END_DATE)
        signup_source = sample_channel(channel_mix, rng, signup_date)

        pre_signup_gap = int(rng.integers(0, 15))
        pre_signup_first_seen = max(START_DATE, signup_date - datetime.timedelta(days=pre_signup_gap))
        # Deterministic (hash of customer_id), NOT uuid.uuid4() -- uuid4() draws
        # from os.urandom, invisible to (and unaffected by) the seeded rng, so a
        # rerun of this script would mint a completely different anon_id for
        # every customer while leaving every OTHER random draw identical. That
        # silently breaks devices.csv/identity_map.csv (built by separate
        # scripts, at a different time, from whatever anon_ids this file had
        # when THEY last ran) without changing anything else -- caught when a
        # routine rebuild here broke both of those already-shipped tables'
        # exact-match validator checks. A hash keyed on customer_id needs no
        # rng draws at all, so it doesn't perturb any other simulated value.
        pre_signup_anon_id = "anon_" + hashlib.md5(f"presignup_{customer_id}".encode()).hexdigest()[:16]

        account_type = "subscriber" if rng.random() < EVER_SUBSCRIBE_RATE else "course_merch_only"

        trial = None
        intervals, sub_events, churn_date, reactivations, churn_segment = [], [], None, [], None
        orders = []

        if account_type == "subscriber":
            trial_start = signup_date
            trial_end = trial_start + datetime.timedelta(days=TRIAL_DAYS)
            if trial_end >= END_DATE:
                # Signed up too close to the dataset's end date for the trial to
                # have resolved yet -- can't be "converted" with zero runway left
                # to actually show a subscription interval. Trial is still pending.
                outcome = "trial_in_progress"
            else:
                roll = rng.random()
                if roll < TRIAL_CONVERSION_RATE:
                    outcome = "converted"
                elif roll < TRIAL_CONVERSION_RATE + TRIAL_CANCEL_RATE:
                    outcome = "canceled_during_trial"
                else:
                    outcome = "expired_passively"
            trial = {"start": trial_start.isoformat(), "end": trial_end.isoformat(),
                     "outcome": outcome, "trigger": "signup"}

            if outcome == "converted":
                initial_plan = "basic" if rng.random() < BASIC_PLAN_SHARE else "plus"
                intervals, sub_events, churn_date, reactivations, churn_segment = simulate_subscription_lifecycle(
                    rng, trial_end, initial_plan, END_DATE)

            sub_windows = active_subscription_windows(intervals)
            orders = generate_orders(rng, signup_date, END_DATE, account_type, sub_windows, churn_date)

        else:
            # course_merch_only: build their organic order history first (no
            # subscription windows exist yet), then roll whether a targeted
            # "come back and subscribe" email eventually reaches them based on
            # that purchase history.
            orders = generate_orders(rng, signup_date, END_DATE, account_type, [], None)
            email_trial = maybe_trigger_merch_to_sub_email(rng, orders, END_DATE)
            if email_trial is not None:
                trial = email_trial
                if trial["outcome"] == "converted":
                    initial_plan = "basic" if rng.random() < BASIC_PLAN_SHARE else "plus"
                    trial_end_date = datetime.date.fromisoformat(trial["end"])
                    intervals, sub_events, churn_date, reactivations, churn_segment = simulate_subscription_lifecycle(
                        rng, trial_end_date, initial_plan, END_DATE)
                    sub_windows = active_subscription_windows(intervals)
                    orders = _reconcile_orders_with_subscription_windows(orders, sub_windows)
                    post_orders = generate_orders(
                        rng, trial_end_date, END_DATE, "subscriber", sub_windows, churn_date)
                    orders = orders + post_orders

        orders.sort(key=lambda o: o["date"])
        ever_converted = trial is not None and trial["outcome"] == "converted"
        engagement_tier = assign_engagement_tier(rng, ever_converted, churn_date)

        timelines.append({
            "customer_id": customer_id,
            "signup_date": signup_date.isoformat(),
            "signup_source": signup_source,
            "pre_signup_anonymous_id": pre_signup_anon_id,
            "pre_signup_first_seen": pre_signup_first_seen.isoformat(),
            "account_type": account_type,
            "trial": trial,
            "churn_segment": churn_segment,
            "subscription_intervals": intervals,
            "subscription_events": sub_events,
            "order_events": orders,
            "churn_date": churn_date,
            "engagement_tier": engagement_tier,
            "reactivations": reactivations,
        })

        attribution.append({
            "customer_id": customer_id,
            "true_acquisition_channel": signup_source,
            "true_acquisition_date": signup_date.isoformat(),
            "reactivation_events": reactivations,
            "merch_to_subscriber_email_trigger": (
                {"trigger_date": trial["start"], "converted": trial["outcome"] == "converted"}
                if (trial is not None and trial.get("trigger") == "email_reactivation") else None
            ),
        })

    return timelines, attribution


def build_summary_frame(timelines):
    rows = []
    for t in timelines:
        active_sub = any(iv["end"] is None for iv in t["subscription_intervals"])
        current_plan = next((iv["plan"] for iv in t["subscription_intervals"] if iv["end"] is None), None)
        rows.append({
            "customer_id": t["customer_id"],
            "signup_date": t["signup_date"],
            "signup_source": t["signup_source"],
            "account_type": t["account_type"],
            "trial_outcome": t["trial"]["outcome"] if t["trial"] else None,
            "churn_segment": t["churn_segment"],
            "num_subscription_intervals": len(t["subscription_intervals"]),
            "currently_active_subscriber": active_sub,
            "current_plan": current_plan,
            "churn_date": t["churn_date"],
            "num_orders": len(t["order_events"]),
            "lifetime_order_value": round(sum(o["amount"] for o in t["order_events"]), 2),
            "engagement_tier": t["engagement_tier"],
            "num_reactivations": len(t["reactivations"]),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    timelines, attribution = simulate_all_customers()

    with open("../internal/_sim_customer_timeline.json", "w") as f:
        json.dump(timelines, f, indent=2)
    with open("../internal/_sim_attribution_ground_truth.json", "w") as f:
        json.dump(attribution, f, indent=2)

    summary = build_summary_frame(timelines)
    summary.to_csv("../internal/_sim_customer_timeline_summary.csv", index=False)

    print(f"Simulated {len(timelines)} customers\n")
    print("--- Account type split ---")
    print(summary["account_type"].value_counts().to_string())
    print("\n--- Trial outcome (all trials: signup + email-triggered) ---")
    print(summary["trial_outcome"].value_counts(dropna=True).to_string())
    denom = summary["trial_outcome"].notna().sum()
    print(f"\nRealized trial conversion rate: "
          f"{(summary['trial_outcome'] == 'converted').sum() / denom:.2%}")
    print("\n--- Currently active subscribers ---")
    print(summary["currently_active_subscriber"].value_counts().to_string())
    ever_paid = summary[summary["trial_outcome"] == "converted"]
    print(f"\nOf {len(ever_paid)} who ever converted, "
          f"{ever_paid['currently_active_subscriber'].sum()} are active today "
          f"({ever_paid['currently_active_subscriber'].mean():.1%})")

    email_triggered = [t for t in timelines if t["trial"] and t["trial"].get("trigger") == "email_reactivation"]
    email_converted = [t for t in email_triggered if t["trial"]["outcome"] == "converted"]
    email_active_today = [t for t in email_converted if t["churn_date"] is None]
    print("\n--- Email-triggered trials (course/merch-only -> subscriber) ---")
    print(f"{len(email_triggered)} customers received the trigger; "
          f"{len(email_converted)} converted "
          f"({len(email_converted)/max(1,len(email_triggered)):.1%}); "
          f"{len(email_active_today)} of those are still active today")

    reactivation_months = [
        datetime.date.fromisoformat(r["reactivated_at"]).month
        for t in timelines for r in t["reactivations"]
    ]
    if reactivation_months:
        from collections import Counter
        counts = Counter(reactivation_months)
        print(f"\n--- Reactivation month distribution ({len(reactivation_months)} total) ---")
        for m in range(1, 13):
            print(f"  {m:2d}: {counts.get(m, 0)}")
