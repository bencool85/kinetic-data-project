"""
Validation for `tiktok_campaigns` (Phase 7, TikTok table 1 of 4 -- last
platform) -- pandas-based, 5-layer approach. Same structural class as
validate_meta_campaigns.py / validate_snap_campaigns.py.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    campaigns = pd.read_csv("../data/tiktok_campaigns.csv")

    # --- 1. Structural ---
    check("Structural", "campaign_id non-null and unique",
          campaigns["campaign_id"].notna().all() and campaigns["campaign_id"].is_unique)
    check("Structural", "advertiser_id, campaign_name, ad_objective, objective_type, budget_mode, "
                       "budget_micro, status non-null on every row",
          campaigns[["advertiser_id", "campaign_name", "ad_objective", "objective_type", "budget_mode",
                     "budget_micro", "status"]].notna().all().all())
    check("Structural", "ad_objective is always one of the 5 shared objectives",
          campaigns["ad_objective"].isin(["prospecting", "retargeting", "lookalike", "conversion", "brand_lift"]).all())
    check("Structural", "objective_type is a valid TikTok Ads Manager objective enum value",
          campaigns["objective_type"].isin(["REACH", "CONVERSIONS", "TRAFFIC", "APP_PROMOTION", "ENGAGEMENT"]).all())
    check("Structural", "budget_mode is a valid TikTok enum value",
          campaigns["budget_mode"].isin(["BUDGET_MODE_DAY", "BUDGET_MODE_TOTAL"]).all())
    check("Structural", "status is a valid TikTok campaign status",
          campaigns["status"].isin(["CAMPAIGN_STATUS_ENABLE", "CAMPAIGN_STATUS_DISABLE"]).all())
    check("Structural", "advertiser_id is the SAME single value on every row",
          campaigns["advertiser_id"].nunique() == 1)

    # --- 2. Referential integrity ---
    check("Referential", "n/a -- this is a root definitions table with no FKs of its own", True)

    # --- 3. Temporal ordering ---
    campaigns["create_time"] = pd.to_datetime(campaigns["create_time"])
    campaigns["start_time"] = pd.to_datetime(campaigns["start_time"])
    check("Temporal", "create_time is always at or before start_time",
          (campaigns["create_time"] <= campaigns["start_time"]).all())
    with_end = campaigns[campaigns["end_time"].notna()].copy()
    with_end["end_time"] = pd.to_datetime(with_end["end_time"])
    check("Temporal", "end_time (where set) is always after start_time",
          (with_end["end_time"] > with_end["start_time"]).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "ad_objective is unique among the 4 evergreen campaigns",
          not campaigns.loc[campaigns["ad_objective"] != "brand_lift", "ad_objective"].duplicated().any())
    check("Business rule", "brand_lift campaigns use BUDGET_MODE_TOTAL (flighted) and REACH objective; "
                          "evergreen campaigns use BUDGET_MODE_DAY and have no end_time",
          (campaigns.loc[campaigns["ad_objective"] == "brand_lift", "budget_mode"] == "BUDGET_MODE_TOTAL").all()
          and (campaigns.loc[campaigns["ad_objective"] == "brand_lift", "objective_type"] == "REACH").all()
          and (campaigns.loc[campaigns["ad_objective"] != "brand_lift", "budget_mode"] == "BUDGET_MODE_DAY").all()
          and campaigns.loc[campaigns["ad_objective"] != "brand_lift", "end_time"].isna().all())

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
