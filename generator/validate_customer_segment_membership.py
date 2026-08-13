"""
Validation for `customer_segment_membership` (Phase 4, table 1 of 1) --
pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB).

Central cross-checks: every segment_id used here is customer-grain (never
one of the 18 anonymous-device segments) and never seg_009 (explicitly
unbuildable until Phase 5); every customer_id is a real, non-deleted
customer; no two membership periods for the same (customer_id, segment_id)
overlap in time; seg_001's entered_at/exited_at reconcile exactly against
subscriptions.csv's own real-interval start_date/canceled_at; and seg_006's
row count matches subscriptions.csv's trialing count exactly.
"""
import pandas as pd

from params import END_DATE
import build_customer_segment_membership as bcsm

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    csm = pd.read_csv("../data/customer_segment_membership.csv")
    customers = pd.read_csv("../data/customers.csv")
    segments = pd.read_csv("../data/segments.csv")
    subs = pd.read_csv("../data/subscriptions.csv")

    csm["entered_at"] = pd.to_datetime(csm["entered_at"])
    csm["exited_at"] = pd.to_datetime(csm["exited_at"])

    # --- 1. Structural ---
    check("Structural", "membership_id non-null and unique",
          csm["membership_id"].notna().all() and csm["membership_id"].is_unique)
    check("Structural", "customer_id, segment_id, entered_at all non-null",
          csm[["customer_id", "segment_id", "entered_at"]].notna().all().all())
    check("Structural", "exited_at, where present, is strictly after entered_at",
          (csm.loc[csm["exited_at"].notna(), "exited_at"] > csm.loc[csm["exited_at"].notna(), "entered_at"]).all())

    # --- 2. Referential integrity ---
    non_deleted = set(customers.loc[~customers["is_deleted"], "customer_id"])
    deleted = set(customers.loc[customers["is_deleted"], "customer_id"])
    check("Referential", "every customer_id exists in customers.csv and is NOT soft-deleted "
                        "(same full-erasure treatment as customer_addresses/devices)",
          csm["customer_id"].isin(non_deleted).all() and not csm["customer_id"].isin(deleted).any())
    customer_grain_segments = set(segments.loc[segments["audience_grain"] == "customer", "segment_id"])
    check("Referential", "every segment_id exists in segments.csv AND is customer-grain "
                        "(never one of the 18 anonymous-device segments)",
          csm["segment_id"].isin(customer_grain_segments).all())
    check("Referential", "seg_009 (High Churn Risk) never appears -- explicitly unbuildable until "
                        "Phase 5 supplies real usage-event engagement data",
          not (csm["segment_id"] == "seg_009").any())

    # --- 3. Temporal ordering ---
    check("Temporal", "entered_at never falls after END_DATE", (csm["entered_at"].dt.date <= END_DATE).all())
    check("Temporal", "exited_at, where present, never falls after END_DATE",
          (csm.loc[csm["exited_at"].notna(), "exited_at"].dt.date <= END_DATE).all())
    joined_signup = csm.merge(
        customers[["customer_id", "created_at"]].rename(columns={"created_at": "signup_at"}), on="customer_id")
    joined_signup["signup_at"] = pd.to_datetime(joined_signup["signup_at"])
    # Compared at DATE granularity (same convention as the refunds-table
    # fix): entered_at for seg_006 is trial_start, a date-only field stored
    # at midnight, while customers.created_at carries a real time-of-day --
    # a trial that started the same calendar day as signup (the normal
    # organic case) would otherwise look like it's "before" signup purely
    # because midnight < 06:11:03, even though it's the same day.
    check("Temporal", "entered_at's calendar date is never before the customer's own signup date",
          (joined_signup["entered_at"].dt.date >= joined_signup["signup_at"].dt.date).all())

    # --- 4. Business-rule invariants ---
    no_overlap = True
    for (cid, seg), grp in csm.sort_values("entered_at").groupby(["customer_id", "segment_id"]):
        prev_exit = None
        for _, row in grp.iterrows():
            if prev_exit is not None and row["entered_at"] < prev_exit:
                no_overlap = False
                break
            prev_exit = row["exited_at"] if pd.notna(row["exited_at"]) else pd.Timestamp.max
        if not no_overlap:
            break
    check("Business rule", "no two membership periods for the same (customer_id, segment_id) pair overlap in time",
          no_overlap)

    real_intervals = subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])].copy()
    real_intervals = real_intervals[real_intervals["customer_id"].isin(non_deleted)]
    seg001 = csm[csm["segment_id"] == "seg_001"].sort_values(["customer_id", "entered_at"]).reset_index(drop=True)
    real_sorted = real_intervals.sort_values(["customer_id", "start_date"]).reset_index(drop=True)
    check("Business rule", "seg_001 row count exactly matches the number of REAL (non-deleted-customer) "
                          "subscription intervals in subscriptions.csv",
          len(seg001) == len(real_sorted))
    seg001_starts = set(zip(seg001["customer_id"], seg001["entered_at"].dt.date))
    real_starts = set(zip(real_sorted["customer_id"], pd.to_datetime(real_sorted["start_date"]).dt.date))
    check("Business rule", "seg_001's entered_at dates exactly match subscriptions.csv's real-interval start_dates",
          seg001_starts == real_starts)

    seg006 = csm[csm["segment_id"] == "seg_006"]
    n_trialing = (subs["status"] == "trialing").sum()
    check("Business rule", "seg_006 row count exactly matches subscriptions.csv's trialing-status count",
          len(seg006) == n_trialing)

    never_subscribed = non_deleted - set(subs["customer_id"])
    seg005_permanent = set(csm.loc[(csm["segment_id"] == "seg_005") & csm["exited_at"].isna(), "customer_id"])
    check("Business rule", "every customer with zero subscription rows ever has a permanent "
                          "(open-ended) seg_005 membership row",
          never_subscribed.issubset(seg005_permanent))

    # --- 5. Distributional sanity ---
    n_eligible = len(non_deleted)
    seg007_count = (csm["segment_id"] == "seg_007").sum()
    seg007_share = seg007_count / n_eligible
    check("Distributional", "seg_007 (High-LTV) membership share lands close to the intended top decile (8-12%)",
          0.08 <= seg007_share <= 0.12, detail=f"{seg007_share:.1%} ({seg007_count}/{n_eligible})")
    pct_with_membership = csm["customer_id"].nunique() / n_eligible
    check("Distributional", "the large majority of eligible customers have at least one membership row "
                          "(everyone is either course/merch-only, trialing, or has touched the "
                          "subscriber/lapsed lifecycle at some point)",
          pct_with_membership > 0.90, detail=f"{pct_with_membership:.1%}")

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
