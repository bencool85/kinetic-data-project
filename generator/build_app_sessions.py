"""
Phase 5 - app_sessions table (3 of 4). In-app fitness usage -- NOT the
marketing/storefront browsing already covered by web_sessions. This is
where the actual product experience (workouts, classes) happens, so unlike
web_sessions, customer_id is ALWAYS present (the app requires being logged
into an account; there's no anonymous app usage in this dataset) and
there's no UTM attribution (nobody discovers the app via an ad click while
already inside it).

Two, independent reasons a non-deleted customer gets app_sessions rows,
neither invented independently -- both derived from real rows already
shipped in subscriptions.csv / orders.csv:

1. **Real subscription intervals** (the same population as
   customer_segment_membership's seg_001) get ongoing usage sessions spread
   across [start_date, canceled_at-or-END_DATE], at a weekly rate keyed by
   `engagement_tier` -- power/regular/casual, read from the master timeline
   (the same field web_sessions.csv's "filler" browsing volume is keyed
   off). This is the direct fulfillment of generation_plan.md's cross-phase
   commitment #2: app usage volume must be sized off the SAME engagement
   signal driving segment membership and web browsing volume, not a
   separately-invented one. Usage stops the moment a subscription lapses --
   access requires an active subscription, standard SaaS behavior.
2. **Course orders** (order_type == 'course' in orders.csv, any known,
   non-deleted customer, independent of subscription status -- courses are
   a la carte and don't require a subscription) get a burst of 3-10
   sessions in the ~45 days after the order date, representing someone
   working through the course content they just bought. Burst size is also
   loosely scaled by engagement_tier.

Merch-only purchases generate no app usage at all (nothing to access
in-app). Guests and soft-deleted customers get zero rows, same treatment
as every other Phase 1/5 operational table.

Each session is pinned to the customer's PRIMARY device (the one carrying
their `pre_signup_anonymous_id`, i.e. devices.csv's first row per
customer_id -- second devices aren't separately modeled for app usage,
same simplification web_sessions.csv already made), and `platform` mirrors
that device's own `device_type` for consistency (never independently
re-rolled).

Output: data/app_sessions.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED, END_DATE
from build_customers import customer_id_for

APP_SESSIONS_PER_WEEK_BY_TIER = {"power": 4.5, "regular": 1.5, "casual": 0.4}
COURSE_SESSION_COUNT_RANGE_BY_TIER = {"power": (5, 10), "regular": (3, 7), "casual": (1, 4)}
COURSE_ACCESS_WINDOW_DAYS = 45


def _session_duration(rng):
    minutes = int(round(float(np.clip(rng.gamma(shape=3.0, scale=10.0), 10.0, 75.0))))
    return datetime.timedelta(minutes=minutes)


def _random_time_of_day(rng):
    return datetime.time(int(rng.integers(5, 23)), int(rng.integers(0, 60)))


def build_app_sessions(seed=SEED + 17):
    rng = np.random.default_rng(seed)
    customers = pd.read_csv("../data/customers.csv")
    subs = pd.read_csv("../data/subscriptions.csv")
    orders = pd.read_csv("../data/orders.csv")
    devices = pd.read_csv("../data/devices.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    non_deleted = customers[~customers["is_deleted"]]
    non_deleted_ids = set(non_deleted["customer_id"])
    engagement_tier = {
        customer_id_for(t["customer_id"]): t["engagement_tier"] for t in timeline
    }

    primary_device = (
        devices.dropna(subset=["customer_id"])
        .sort_values("device_id")
        .groupby("customer_id")
        .first()[["device_id", "device_type"]]
    )

    real_intervals = subs[
        (subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"]))
        & subs["customer_id"].isin(non_deleted_ids)
    ]
    course_orders = orders[
        (orders["order_type"] == "course") & orders["customer_id"].notna()
        & orders["customer_id"].isin(non_deleted_ids)
    ]

    rows = []

    def emit(cid, started_at, device_row):
        rows.append({
            "customer_id": cid,
            "device_id": device_row["device_id"],
            "platform": device_row["device_type"],
            "started_at": started_at,
            "ended_at": started_at + _session_duration(rng),
        })

    # --- 1. Subscription-driven usage ---
    for row in real_intervals.itertuples():
        cid = row.customer_id
        if cid not in primary_device.index:
            continue
        device_row = primary_device.loc[cid]
        tier = engagement_tier.get(cid, "casual")
        start = datetime.date.fromisoformat(row.start_date)
        end = datetime.date.fromisoformat(row.canceled_at) if pd.notna(row.canceled_at) else END_DATE
        end = min(end, END_DATE)
        weeks = max(0.0, (end - start).days / 7.0)
        n_sessions = int(rng.poisson(APP_SESSIONS_PER_WEEK_BY_TIER[tier] * weeks))
        span_days = max(1, (end - start).days)
        for _ in range(n_sessions):
            offset_days = int(rng.integers(0, span_days + 1))
            session_date = start + datetime.timedelta(days=offset_days)
            if session_date > END_DATE:
                continue
            started_at = datetime.datetime.combine(session_date, _random_time_of_day(rng))
            emit(cid, started_at, device_row)

    # --- 2. Course-access usage ---
    for order in course_orders.itertuples():
        cid = order.customer_id
        if cid not in primary_device.index:
            continue
        device_row = primary_device.loc[cid]
        tier = engagement_tier.get(cid, "casual")
        lo, hi = COURSE_SESSION_COUNT_RANGE_BY_TIER[tier]
        n_sessions = int(rng.integers(lo, hi + 1))
        order_date = datetime.date.fromisoformat(order.order_date)
        window_end = min(order_date + datetime.timedelta(days=COURSE_ACCESS_WINDOW_DAYS), END_DATE)
        span_days = max(1, (window_end - order_date).days)
        for _ in range(n_sessions):
            offset_days = int(rng.integers(0, span_days + 1))
            session_date = order_date + datetime.timedelta(days=offset_days)
            if session_date > END_DATE:
                continue
            started_at = datetime.datetime.combine(session_date, _random_time_of_day(rng))
            emit(cid, started_at, device_row)

    df = pd.DataFrame(rows).sort_values("started_at").reset_index(drop=True)
    df.insert(0, "session_id", [f"app_sess_{i:07d}" for i in range(1, len(df) + 1)])
    df["started_at"] = df["started_at"].apply(lambda d: d.isoformat())
    df["ended_at"] = df["ended_at"].apply(lambda d: d.isoformat())
    return df


if __name__ == "__main__":
    df = build_app_sessions()
    df.to_csv("../data/app_sessions.csv", index=False)
    print(f"Wrote {len(df)} app_sessions\n")
    print(f"Unique customers: {df['customer_id'].nunique()}")
    print(df["platform"].value_counts(normalize=True).round(3).to_string())
    print(df.groupby("customer_id").size().describe())
