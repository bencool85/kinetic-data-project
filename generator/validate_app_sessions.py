"""
Validation for `app_sessions` (Phase 5, table 3 of 4) -- pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

Central cross-checks: every session's device_id genuinely belongs to that
same customer_id in devices.csv, and platform matches that device's own
device_type exactly (never independently re-rolled); every session date
falls inside either a real subscription interval or a course's 45-day
access window for that customer (never invented usage with no underlying
reason); and customers with neither a real subscription interval nor a
course order get ZERO rows (no usage without something to use).
"""
import datetime
import json
import pandas as pd

from params import SEED, END_DATE
import build_app_sessions as bas
from build_customers import customer_id_for

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    sessions = pd.read_csv("../data/app_sessions.csv")
    customers = pd.read_csv("../data/customers.csv")
    subs = pd.read_csv("../data/subscriptions.csv")
    orders = pd.read_csv("../data/orders.csv")
    devices = pd.read_csv("../data/devices.csv")

    sessions["started_at"] = pd.to_datetime(sessions["started_at"])
    sessions["ended_at"] = pd.to_datetime(sessions["ended_at"])

    # --- 1. Structural ---
    check("Structural", "session_id non-null and unique",
          sessions["session_id"].notna().all() and sessions["session_id"].is_unique)
    check("Structural", "customer_id, device_id, platform all non-null on every row",
          sessions[["customer_id", "device_id", "platform"]].notna().all().all())
    check("Structural", "ended_at is always after started_at",
          (sessions["ended_at"] > sessions["started_at"]).all())
    durations_min = (sessions["ended_at"] - sessions["started_at"]).dt.total_seconds() / 60
    check("Structural", "session duration is always in the 10-75 minute band (workout-length sessions)",
          ((durations_min >= 10) & (durations_min <= 75)).all())

    # --- 2. Referential integrity ---
    non_deleted = customers.loc[~customers["is_deleted"]]
    non_deleted_ids = set(non_deleted["customer_id"])
    check("Referential", "every customer_id exists in customers.csv and is NOT soft-deleted",
          sessions["customer_id"].isin(non_deleted_ids).all())
    device_owner = devices.set_index("device_id")["customer_id"]
    check("Referential", "every device_id exists in devices.csv AND genuinely belongs to that same "
                        "session's customer_id (never a mismatched or anonymous device)",
          sessions["device_id"].isin(device_owner.index).all()
          and (sessions["device_id"].map(device_owner) == sessions["customer_id"]).all())
    device_type = devices.set_index("device_id")["device_type"]
    check("Referential", "platform exactly matches that device's own device_type in devices.csv "
                        "(never independently re-rolled)",
          (sessions["device_id"].map(device_type) == sessions["platform"]).all())

    # --- 3. Temporal ordering ---
    check("Temporal", "no session starts after END_DATE", (sessions["started_at"].dt.date <= END_DATE).all())

    real_intervals = subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])].copy()
    real_intervals = real_intervals[real_intervals["customer_id"].isin(non_deleted_ids)]
    sub_windows = {}
    for row in real_intervals.itertuples():
        end = datetime.date.fromisoformat(row.canceled_at) if pd.notna(row.canceled_at) else END_DATE
        sub_windows.setdefault(row.customer_id, []).append(
            (datetime.date.fromisoformat(row.start_date), min(end, END_DATE)))

    course_orders = orders[(orders["order_type"] == "course") & orders["customer_id"].notna()
                            & orders["customer_id"].isin(non_deleted_ids)]
    course_windows = {}
    for row in course_orders.itertuples():
        start = datetime.date.fromisoformat(row.order_date)
        end = min(start + datetime.timedelta(days=bas.COURSE_ACCESS_WINDOW_DAYS), END_DATE)
        course_windows.setdefault(row.customer_id, []).append((start, end))

    def has_a_reason(cid, date):
        for lo, hi in sub_windows.get(cid, []):
            if lo <= date <= hi:
                return True
        for lo, hi in course_windows.get(cid, []):
            if lo <= date <= hi:
                return True
        return False

    sessions["date"] = sessions["started_at"].dt.date
    covered = sessions.apply(lambda r: has_a_reason(r["customer_id"], r["date"]), axis=1)
    check("Temporal", "every session date falls inside either a real subscription interval or a "
                    "course's 45-day access window for that same customer (no usage without a reason)",
          covered.all())

    # --- 4. Business-rule invariants ---
    eligible_ids = set(real_intervals["customer_id"]) | set(course_orders["customer_id"])
    ineligible_ids = non_deleted_ids - eligible_ids
    check("Business rule", "customers with neither a real subscription interval nor a course order "
                          "(merch-only or never-purchased) have ZERO app_sessions rows",
          not sessions["customer_id"].isin(ineligible_ids).any())

    # --- 5. Distributional sanity ---
    # Not an exact match by design: a Poisson-distributed session count can
    # legitimately land on 0 for a short-tenure casual-tier subscriber (e.g.
    # a ~1-month interval at the casual rate has ~18% chance of zero opens
    # before churning) -- that's a realistic "signed up, never really used
    # it, canceled" outcome, not a bug. Checked as a small tolerance band
    # instead of an exact match.
    n_customers = sessions["customer_id"].nunique()
    gap = len(eligible_ids) - n_customers
    check("Distributional", "the number of distinct customers with app usage is within a small tolerance "
                          "of the eligible (subscriber-or-course-buyer) population (a few legitimate "
                          "zero-usage short-tenure churners are expected)",
          0 <= gap <= 15, detail=f"{n_customers} vs {len(eligible_ids)} eligible ({gap} zero-usage)")
    platform_share = sessions["platform"].value_counts(normalize=True)
    device_share = devices.dropna(subset=["customer_id"])["device_type"].value_counts(normalize=True)
    check("Distributional", "platform mix is within 10 points of the overall known-device population's "
                          "device_type mix (sessions aren't skewed toward one platform by construction)",
          all(abs(platform_share.get(k, 0) - device_share.get(k, 0)) < 0.10 for k in device_share.index))

    n_fail = sum(1 for _, _, ok, _ in results if not ok)
    for layer, name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {layer}: {name}" + (f"  -- {detail}" if detail else ""))
    print(f"\n{len(results) - n_fail}/{len(results)} checks passed")
    return n_fail == 0


if __name__ == "__main__":
    ok = run()
    if not ok:
        raise SystemExit(1)
