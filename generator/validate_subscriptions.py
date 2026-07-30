"""
Validation for `subscriptions` (Phase 2, table 1 of 3) -- pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

The central cross-check this table needs isn't just "does every row look
individually valid" -- it's "does the number and shape of subscription
objects reconcile EXACTLY against the master timeline's trial/interval
structure", and "does the current_period_end math actually guarantee a
real, future-dated renewal for every open subscription" (that's the whole
point of building this table: it's what the 'High Churn Risk' segment has
been waiting on since Phase 1).
"""
import datetime
import json
import pandas as pd

from params import END_DATE, BASIC_PLAN_SHARE, ANNUAL_BILLING_SHARE, INVOLUNTARY_CHURN_SHARE

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    subs = pd.read_csv("../data/subscriptions.csv")
    customers = pd.read_csv("../data/customers.csv")
    plans = pd.read_csv("../data/subscription_plans.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    for col in ["trial_start", "trial_end", "start_date", "current_period_start",
                "current_period_end", "canceled_at", "created_at"]:
        subs[col] = pd.to_datetime(subs[col])

    # --- 1. Structural ---
    check("Structural", "subscription_id non-null and unique",
          subs["subscription_id"].notna().all() and subs["subscription_id"].is_unique)
    check("Structural", "customer_id non-null", subs["customer_id"].notna().all())
    check("Structural", "plan_id non-null and every value exists in subscription_plans",
          subs["plan_id"].notna().all() and subs["plan_id"].isin(plans["plan_id"]).all())
    check("Structural", "billing_interval in {month, year}", subs["billing_interval"].isin(["month", "year"]).all())
    check("Structural", "status in {trialing, active, past_due, canceled, paused}",
          subs["status"].isin(["trialing", "active", "past_due", "canceled", "paused"]).all())
    check("Structural", "current_period_start <= current_period_end for every row",
          (subs["current_period_start"] <= subs["current_period_end"]).all())
    check("Structural", "trial_start <= trial_end wherever both are populated",
          (subs.dropna(subset=["trial_start", "trial_end"])["trial_start"]
           <= subs.dropna(subset=["trial_start", "trial_end"])["trial_end"]).all())
    check("Structural", "canceled_at populated if and only if status == 'canceled'",
          (subs["status"].eq("canceled") == subs["canceled_at"].notna()).all())
    check("Structural", "cancel_reason populated if and only if status == 'canceled'",
          (subs["status"].eq("canceled") == subs["cancel_reason"].notna()).all())
    check("Structural", "cancel_reason in {voluntary, involuntary, trial_expired, trial_canceled} wherever populated",
          subs["cancel_reason"].dropna().isin(["voluntary", "involuntary", "trial_expired", "trial_canceled"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every subscriptions.customer_id exists in customers.csv",
          subs["customer_id"].isin(customers["customer_id"]).all())
    check("Referential", "billing_interval matches the billing_interval on the row's own plan_id "
                          "(denormalized column never drifts from its FK'd source of truth)",
          (subs.merge(plans[["plan_id", "billing_interval"]], on="plan_id", suffixes=("", "_plan"))
           .pipe(lambda d: (d["billing_interval"] == d["billing_interval_plan"]).all()))
          if len(subs) else True)

    # Exact row-count reconciliation against the timeline: one subscription
    # object per (trial-that-never-converted OR trial-that-converted-plus-
    # every-interval) -- i.e. max(1, len(intervals)) per customer with a
    # trial, 0 for customers with no trial at all.
    expected_total = sum(
        max(1, len(t["subscription_intervals"])) for t in timeline if t["trial"] is not None
    )
    check("Referential", "total subscription row count exactly reconciles against the timeline's "
                          "trial/interval structure (one object per trial-or-interval)",
          len(subs) == expected_total, f"{len(subs)} rows vs. {expected_total} expected from the timeline")

    n_customers_with_trial = sum(1 for t in timeline if t["trial"] is not None)
    check("Referential", "every customer with a trial in the timeline has at least one subscription row",
          subs["customer_id"].nunique() == n_customers_with_trial,
          f"{subs['customer_id'].nunique()} distinct customers in subscriptions vs. {n_customers_with_trial} with a trial")

    # --- 3. Temporal ordering ---
    customer_created = customers[["customer_id", "created_at"]].rename(columns={"created_at": "customer_created_at"})
    check("Temporal", "trial_start (when present) is on/after the customer's own created_at date",
          subs.merge(customer_created, on="customer_id")
              .assign(created_date=lambda d: pd.to_datetime(d["customer_created_at"]).dt.normalize())
              .dropna(subset=["trial_start"])
              .pipe(lambda d: (d["trial_start"] >= d["created_date"]).all()))

    open_statuses = subs["status"].isin(["active", "past_due"])
    check("Temporal", "every 'active'/'past_due' subscription has current_period_end strictly after END_DATE "
                      "(a real, still-future renewal date -- this is the whole point of the table)",
          (subs.loc[open_statuses, "current_period_end"] > pd.Timestamp(END_DATE)).all())

    trialing = subs["status"] == "trialing"
    check("Temporal", "every 'trialing' subscription has trial_end on/after END_DATE (still unresolved as of the snapshot)",
          (subs.loc[trialing, "trial_end"] >= pd.Timestamp(END_DATE)).all())

    canceled = subs["status"] == "canceled"
    check("Temporal", "every 'canceled' subscription has canceled_at on/before END_DATE, and current_period_end == canceled_at",
          (subs.loc[canceled, "canceled_at"] <= pd.Timestamp(END_DATE)).all()
          and (subs.loc[canceled, "current_period_end"] == subs.loc[canceled, "canceled_at"]).all())

    past_due = subs["status"] == "past_due"
    check("Temporal", "every 'past_due' subscription's current_period_start falls within the recent "
                      "grace-period window of END_DATE (that's the only reason it's past_due, not canceled)",
          ((pd.Timestamp(END_DATE) - subs.loc[past_due, "current_period_start"]).dt.days <= 14).all()
          if past_due.any() else True)

    # --- 4. Business-rule invariants ---
    # Reconstruct, per customer, the set of tiers the timeline actually assigned
    # to converted intervals, and confirm subscriptions.csv's plan_id-derived
    # tier matches for every interval_id > 0 row (interval_id 0 = never-converted
    # trial, which has no timeline-assigned tier to check against).
    tier_by_customer_interval = {}
    for t in timeline:
        cid = t["customer_id"]
        for iv in t["subscription_intervals"]:
            tier_by_customer_interval[(cid, iv["interval_id"])] = iv["plan"]

    # subscription_id doesn't carry sim_customer_id/interval_id in the shipped
    # CSV (internal-only fields), so re-derive the same objects in-memory to
    # check tier fidelity without inventing a fragile join.
    import build_subscriptions as bs
    objects = bs.build_subscription_objects(timeline)
    tier_mismatches = 0
    for obj in objects:
        if obj["interval_id"] == 0:
            continue
        expected_tier = tier_by_customer_interval[(obj["sim_customer_id"], obj["interval_id"])]
        actual_tier = obj["plan_id"].split("_")[1]  # plan_{tier}_{monthly|annual}
        if actual_tier != expected_tier:
            tier_mismatches += 1
    check("Business rule", "every converted subscription's plan_id tier matches the timeline's own interval tier exactly",
          tier_mismatches == 0, f"{tier_mismatches} mismatches out of {len(objects)} subscription objects")

    n_open_in_subs = subs["status"].isin(["active", "past_due"]).sum()
    n_open_in_timeline = sum(
        1 for t in timeline if any(iv["end"] is None for iv in t["subscription_intervals"])
    )
    check("Business rule", "count of currently-open subscriptions (active + past_due) exactly matches "
                          "the timeline's count of customers with an open interval (the established '98' figure)",
          n_open_in_subs == n_open_in_timeline, f"{n_open_in_subs} in subscriptions.csv vs. {n_open_in_timeline} in the timeline")

    check("Business rule", "'paused' status is a valid enum value but intentionally has 0 rows "
                          "(not modeled yet -- flagged, not silently omitted)",
          (subs["status"] == "paused").sum() == 0)

    check("Business rule", "no subscription with status='trialing' has a non-null canceled_at",
          subs.loc[subs["status"] == "trialing", "canceled_at"].isna().all())

    n_converted_trials = sum(1 for t in timeline if t["trial"] and t["trial"]["outcome"] == "converted")
    n_case_b_active_or_canceled = sum(
        1 for obj in objects if obj["interval_id"] == 1
    )
    check("Business rule", "every converted trial produced exactly one interval_id==1 subscription object",
          n_case_b_active_or_canceled == n_converted_trials,
          f"{n_case_b_active_or_canceled} vs. {n_converted_trials} converted trials")

    # --- 5. Distributional sanity ---
    annual_share = (subs["billing_interval"] == "year").mean()
    check("Distributional", f"annual billing share ~{ANNUAL_BILLING_SHARE:.0%} (within 5pp)",
          abs(annual_share - ANNUAL_BILLING_SHARE) < 0.05, f"actual: {annual_share:.1%}")

    interval1_tiers = subs[subs["status"].isin(["active", "past_due"]) | (subs["cancel_reason"].isin(["voluntary", "involuntary"]))]
    basic_share_among_paid = (interval1_tiers["plan_id"].str.contains("basic")).mean()
    check("Distributional", f"basic/plus split among ever-paid subscriptions roughly tracks BASIC_PLAN_SHARE ({BASIC_PLAN_SHARE:.0%}) "
                          "-- loose band since resubscribe tiers re-roll independently each time",
          0.55 <= basic_share_among_paid <= 0.90, f"actual basic share: {basic_share_among_paid:.1%}")

    real_churns = subs[subs["cancel_reason"].isin(["voluntary", "involuntary"])]
    involuntary_share = (real_churns["cancel_reason"] == "involuntary").mean() if len(real_churns) else None
    check("Distributional", f"involuntary share of real (non-trial) cancellations ~{INVOLUNTARY_CHURN_SHARE:.0%} (within 10pp)",
          involuntary_share is not None and abs(involuntary_share - INVOLUNTARY_CHURN_SHARE) < 0.10,
          f"actual: {involuntary_share:.1%}" if involuntary_share is not None else "n/a")

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
