"""
Phase 0 - Steps 5 & 6: Per-customer master timeline + attribution ground truth.

For each of the 100 customers, simulates their whole lifecycle as one ground-truth
object: signup, trial, subscription intervals (with churn/win-back), and order
events -- respecting the rule that course purchases never fall inside an active
subscription interval. Every real table built in later phases derives from this.

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
    SUBSCRIPTION_MEAN_TENURE_MONTHS, PLAN_CHANGE_PROBABILITY, INVOLUNTARY_CHURN_SHARE,
    WINBACK_PROBABILITY, WINBACK_GAP_MONTHS_RANGE, PAYMENT_BLIP_PROBS,
    REACTIVATION_CHANNEL_WEIGHTS, COURSE_ORDERS_PER_YEAR_NONSUB_RANGE,
    MERCH_ORDERS_PER_YEAR_RANGE, COURSE_PRICE_TIERS, COURSE_PRICE_WEIGHTS,
    MERCH_PRICE_TIERS, MERCH_PRICE_WEIGHTS, SUBSCRIBER_MERCH_DISCOUNT,
)
from sim_utils import load_calendar, load_channel_mix, sample_weighted_date, sample_channel


def simulate_subscription_lifecycle(rng, start_date, initial_plan, dataset_end):
    """Simulate a converted subscriber's full interval history from trial-end
    forward. Returns (intervals, events, churn_date, reactivation_channels)."""
    intervals, events, reactivation_channels = [], [], []
    cursor = start_date
    interval_num = 0
    churn_date = None

    while cursor < dataset_end:
        interval_num += 1
        plan = initial_plan if interval_num == 1 else str(rng.choice(["basic", "plus"], p=[0.75, 0.25]))

        tenure_months = max(1, int(round(rng.exponential(SUBSCRIPTION_MEAN_TENURE_MONTHS))))
        tentative_end = cursor + relativedelta(months=tenure_months)

        # Resolved payment-failure blips (noise, don't end the subscription)
        n_blips = int(rng.choice(list(PAYMENT_BLIP_PROBS.keys()), p=list(PAYMENT_BLIP_PROBS.values())))
        for _ in range(n_blips):
            offset_days = int(rng.integers(15, max(16, tenure_months * 30)))
            blip_date = cursor + datetime.timedelta(days=offset_days)
            if blip_date < min(tentative_end, dataset_end):
                events.append({"event_type": "payment_failed", "event_at": blip_date.isoformat(),
                               "interval_id": interval_num, "resolved": True})

        # Optional single plan change mid-interval
        if rng.random() < PLAN_CHANGE_PROBABILITY and tentative_end < dataset_end:
            change_offset = int(rng.integers(1, max(2, tenure_months)))
            change_date = cursor + relativedelta(months=change_offset)
            new_plan = "plus" if plan == "basic" else "basic"
            events.append({
                "event_type": "upgraded" if new_plan == "plus" else "downgraded",
                "event_at": change_date.isoformat(), "interval_id": interval_num,
            })
            plan = new_plan

        if tentative_end >= dataset_end:
            # Runs off the end of the dataset -- still active today
            intervals.append({
                "interval_id": interval_num, "plan": plan,
                "start": cursor.isoformat(), "end": None, "end_reason": "ongoing",
            })
            churn_date = None
            break

        end_reason = "involuntary" if rng.random() < INVOLUNTARY_CHURN_SHARE else "voluntary"
        if end_reason == "involuntary":
            events.append({"event_type": "payment_failed", "event_at": tentative_end.isoformat(),
                            "interval_id": interval_num, "resolved": False})
        events.append({"event_type": "canceled", "event_at": tentative_end.isoformat(),
                        "interval_id": interval_num, "reason": end_reason})
        intervals.append({
            "interval_id": interval_num, "plan": plan,
            "start": cursor.isoformat(), "end": tentative_end.isoformat(), "end_reason": end_reason,
        })
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
            initial_plan = plan  # carry the plan forward into the new interval by default
        else:
            break

    return intervals, events, churn_date, reactivation_channels


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


def generate_orders(rng, customer_start, dataset_end, account_type, sub_windows, is_ever_active_at):
    """Generate course + merch order events respecting: course orders never inside
    an active subscription window."""
    orders = []
    active_years = max(0.25, (dataset_end - customer_start).days / 365.25)

    # Course orders -- only for course/merch-only accounts, or subscribers during gaps
    if account_type == "course_merch_only":
        n_courses = int(rng.integers(*COURSE_ORDERS_PER_YEAR_NONSUB_RANGE)) * max(1, round(active_years))
        n_courses = min(n_courses, 8)
        attempts, placed = 0, 0
        while placed < n_courses and attempts < n_courses * 6:
            attempts += 1
            candidate = customer_start + datetime.timedelta(
                days=int(rng.integers(0, max(1, (dataset_end - customer_start).days))))
            if not is_covered(candidate, sub_windows):
                price = round(float(rng.choice(COURSE_PRICE_TIERS, p=COURSE_PRICE_WEIGHTS)), 2)
                orders.append({"order_type": "course", "date": candidate.isoformat(), "amount": price})
                placed += 1
    else:
        # Subscribers might buy a course only in a gap before their first trial,
        # or between/after subscription intervals
        gap_days = sum((min(w[0], dataset_end) - customer_start).days for w in sub_windows if w[0] > customer_start)
        if sub_windows and rng.random() < 0.15 and gap_days > 14:
            pre_trial_end = sub_windows[0][0]
            candidate_span = (pre_trial_end - customer_start).days
            if candidate_span > 0:
                candidate = customer_start + datetime.timedelta(days=int(rng.integers(0, candidate_span)))
                price = round(float(rng.choice(COURSE_PRICE_TIERS, p=COURSE_PRICE_WEIGHTS)), 2)
                orders.append({"order_type": "course", "date": candidate.isoformat(), "amount": price})

    # Merch orders -- anyone, anytime; flag subscriber discount if active at purchase time
    n_merch = int(rng.integers(*MERCH_ORDERS_PER_YEAR_RANGE) * max(1, round(active_years)))
    n_merch = min(n_merch, 10)
    for _ in range(n_merch):
        span = max(1, (dataset_end - customer_start).days)
        candidate = customer_start + datetime.timedelta(days=int(rng.integers(0, span)))
        price = round(float(rng.choice(MERCH_PRICE_TIERS, p=MERCH_PRICE_WEIGHTS)), 2)
        discounted = is_covered(candidate, sub_windows)
        if discounted:
            price = round(price * (1 - SUBSCRIBER_MERCH_DISCOUNT), 2)
        orders.append({"order_type": "merch", "date": candidate.isoformat(), "amount": price,
                        "subscriber_discount_applied": discounted})

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
        intervals, sub_events, churn_date, reactivations = [], [], None, []

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
                intervals, sub_events, churn_date, reactivations = simulate_subscription_lifecycle(
                    rng, trial_end, initial_plan, END_DATE)

        sub_windows = active_subscription_windows(intervals)
        orders = generate_orders(rng, signup_date, END_DATE, account_type, sub_windows, None)
        engagement_tier = assign_engagement_tier(rng, account_type, churn_date)

        timelines.append({
            "customer_id": customer_id,
            "signup_date": signup_date.isoformat(),
            "signup_source": signup_source,
            "pre_signup_anonymous_id": pre_signup_anon_id,
            "pre_signup_first_seen": pre_signup_first_seen.isoformat(),
            "account_type": account_type,
            "trial": trial,
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
    print(f"\nRealized trial conversion rate: "
          f"{(summary['trial_outcome'] == 'converted').sum() / summary['trial_outcome'].notna().sum():.2%}")
    print("\n--- Currently active subscribers ---")
    print(summary["currently_active_subscriber"].value_counts().to_string())
    print("\n--- Current plan (active subscribers) ---")
    print(summary["current_plan"].value_counts(dropna=True).to_string())
    print("\n--- Engagement tier ---")
    print(summary["engagement_tier"].value_counts().to_string())
    print(f"\nAvg orders/customer: {summary['num_orders'].mean():.2f}")
    print(f"Customers with 0 orders: {(summary['num_orders'] == 0).sum()}")
    print(f"Customers with any reactivation: {(summary['num_reactivations'] > 0).sum()}")
