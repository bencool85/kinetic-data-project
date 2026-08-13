"""
Validation for `snap_campaigns` (Phase 7, Snap table 1 of 4) -- pandas-based,
5-layer approach. Same structural class as validate_meta_campaigns.py.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    campaigns = pd.read_csv("../data/snap_campaigns.csv")

    # --- 1. Structural ---
    check("Structural", "campaign_id non-null and unique",
          campaigns["campaign_id"].notna().all() and campaigns["campaign_id"].is_unique)
    check("Structural", "ad_account_id, name, ad_objective, objective, status non-null on every row",
          campaigns[["ad_account_id", "name", "ad_objective", "objective", "status"]].notna().all().all())
    check("Structural", "ad_objective is always one of the 5 shared objectives",
          campaigns["ad_objective"].isin(["prospecting", "retargeting", "lookalike", "conversion", "brand_lift"]).all())
    check("Structural", "objective is a valid Snap Ads API campaign objective enum value",
          campaigns["objective"].isin(["AWARENESS", "WEB_CONVERSIONS", "APP_INSTALLS", "ENGAGEMENT",
                                        "CATALOG_SALES"]).all())
    check("Structural", "status is always a valid Snap campaign status",
          campaigns["status"].isin(["ACTIVE", "PAUSED", "COMPLETED"]).all())
    check("Structural", "exactly one budget field (daily_budget_micro XOR lifetime_budget_micro) is set",
          ((campaigns["daily_budget_micro"].notna()) ^ (campaigns["lifetime_budget_micro"].notna())).all())
    check("Structural", "ad_account_id is the SAME single value on every row",
          campaigns["ad_account_id"].nunique() == 1)

    # --- 2. Referential integrity ---
    check("Referential", "n/a -- this is a root definitions table with no FKs of its own", True)

    # --- 3. Temporal ordering ---
    campaigns["created_at"] = pd.to_datetime(campaigns["created_at"])
    campaigns["start_time"] = pd.to_datetime(campaigns["start_time"])
    check("Temporal", "created_at is always at or before start_time",
          (campaigns["created_at"] <= campaigns["start_time"]).all())
    with_end = campaigns[campaigns["end_time"].notna()].copy()
    with_end["end_time"] = pd.to_datetime(with_end["end_time"])
    check("Temporal", "end_time (where set) is always after start_time",
          (with_end["end_time"] > with_end["start_time"]).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "ad_objective is unique among the 4 evergreen campaigns",
          not campaigns.loc[campaigns["ad_objective"] != "brand_lift", "ad_objective"].duplicated().any())
    check("Business rule", "every brand_lift campaign has a lifetime_budget_micro and is AWARENESS objective",
          campaigns.loc[campaigns["ad_objective"] == "brand_lift", "lifetime_budget_micro"].notna().all()
          and (campaigns.loc[campaigns["ad_objective"] == "brand_lift", "objective"] == "AWARENESS").all())
    check("Business rule", "every evergreen campaign has a daily_budget_micro and no end_time, and is ACTIVE",
          campaigns.loc[campaigns["ad_objective"] != "brand_lift", "daily_budget_micro"].notna().all()
          and campaigns.loc[campaigns["ad_objective"] != "brand_lift", "end_time"].isna().all()
          and (campaigns.loc[campaigns["ad_objective"] != "brand_lift", "status"] == "ACTIVE").all())

    # --- 5. Distributional sanity ---
    n_evergreen = (campaigns["ad_objective"] != "brand_lift").sum()
    n_brand_lift = (campaigns["ad_objective"] == "brand_lift").sum()
    check("Distributional", "4 evergreen campaigns + brand_lift flights",
          n_evergreen == 4 and n_brand_lift >= 1, detail=f"{n_evergreen} evergreen / {n_brand_lift} brand_lift")

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
