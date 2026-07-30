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
import json
import uuid
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from params import (
    SEED, N_CUSTOMERS, START_DATE, END_DATE, TRIAL_DAYS,
    EVER_SUBSCRIBE_RATE, TRIAL_CONVERSION_RATE, TRIAL_CANCEL_RATE, BASIC_PLAN_SHARE,
    LOYAL_SEGMENT_SHARE, QUICK_CHURN_MEAN_TENURE_MONTHS,
    PLAN_CHANGE_PROBABILITY, INVOLUNTARY_CHURN_SHARE,
    WINBACK_PROBABILITY, WINBACK_GAP_MONTHS_RANGE, PAYMENT_BLIP_PROBS,
    REACTIVATION_CHANNEL_WEIGHTS, LAPSED_STILL_BUYING_RATE,
    COURSE_ORDERS_PER_YEAR_NONSUB_RANGE,
    MERCH_ORDERS_PER_YEAR_RANGE, COURSE_PRICE_TIERS, COURSE_PRICE_WEIGHTS,
    MERCH_PRICE_TIERS, MERCH_PRICE_WEIGHTS, SUBSCRIBER_MERCH_DISCOUNT,
)
from sim_utils import load_calendar, load_channel_mix, sample_weighted_date, sample_channel


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
    churn_date, reactivation_channels, segment)."""
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
            gap_months = int(rng.integers(WINBACK_GAP_MONTHS_RANGE[0], WINBACK_GAP_MONTHS_RANGE[1] + 1))
            next_start = tentative_end + relativedelta(months=gap_months)
            if next_start >= dataset_end:
                break
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


def assign_engagement_tier(rng, account_type, churn_date):
    if account_type == "subscriber" and churn_date is None:
        return str(rng.choice(["power", "regular"], p=[0.6, 0.4]))
    if account_type == "subscriber" and churn_date is not None:
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
        pre_signup_anon_id = "anon_" + uuid.uuid4().hex[:16]

        account_type = "subscriber" if rng.random() < EVER_SUBSCRIBE_RATE else "course_merch_only"

        trial = None
        intervals, sub_events, churn_date, reactivations, churn_segment = [], [], None, [], None

        if account_type == "subscriber":
            trial_start = signup_date
            trial_end = trial_start + datetime.timedelta(days=TRIAL_DAYS)
            roll = rng.random()
            if roll < TRIAL_CONVERSION_RATE:
                outcome = "converted"
            elif roll < TRIAL_CONVERSION_RATE + TRIAL_CANCEL_RATE:
                outcome = "canceled_during_trial"
            else:
                outcome = "expired_passively"
            trial = {"start": trial_start.isoformat(), "end": trial_end.isoformat(), "outcome": outcome}

            if outcome == "converted":
                initial_plan = "basic" if rng.random() < BASIC_PLAN_SHARE else "plus"
                intervals, sub_events, churn_date, reactivations, churn_segment = simulate_subscription_lifecycle(
                    rng, trial_end, initial_plan, END_DATE)

        sub_windows = active_subscription_windows(intervals)
        orders = generate_orders(rng, signup_date, END_DATE, account_type, sub_windows, churn_date)
        engagement_tier = assign_engagement_tier(rng, account_type, churn_date)

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
    print("\n--- Trial outcome (subscribers only) ---")
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
