"""
Validation for `google_search_campaigns` (Phase 7, Google Search table 1
of 4) -- pandas-based, 5-layer approach. Lightweight definitions-table
validation, same class as meta_campaigns.py.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    campaigns = pd.read_csv("../data/google_search_campaigns.csv")

    # --- 1. Structural ---
    check("Structural", "campaign_id non-null and unique",
          campaigns["campaign_id"].notna().all() and campaigns["campaign_id"].is_unique)
    check("Structural", "customer_id, name, ad_objective, advertising_channel_type, bidding_strategy_type, "
                       "status, campaign_budget_micros all non-null",
          campaigns[["customer_id", "name", "ad_objective", "advertising_channel_type",
                     "bidding_strategy_type", "status", "campaign_budget_micros"]].notna().all().all())
    check("Structural", "ad_objective is always one of the 5 shared objectives",
          campaigns["ad_objective"].isin(["prospecting", "retargeting", "lookalike", "conversion", "brand_lift"]).all())
    check("Structural", "advertising_channel_type is always SEARCH (this is the Search platform table)",
          (campaigns["advertising_channel_type"] == "SEARCH").all())
    check("Structural", "status is always a valid Google Ads campaign status",
          campaigns["status"].isin(["ENABLED", "PAUSED", "REMOVED"]).all())
    check("Structural", "bidding_strategy_type is a valid Google Ads bidding strategy enum value",
          campaigns["bidding_strategy_type"].isin(["MAXIMIZE_CLICKS", "TARGET_CPA", "MAXIMIZE_CONVERSIONS",
                                                     "TARGET_ROAS", "MANUAL_CPC"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "n/a -- this is a root definitions table with no FKs of its own", True)

    # --- 3. Temporal ordering ---
    campaigns["start_date"] = pd.to_datetime(campaigns["start_date"])
    campaigns["created_at"] = pd.to_datetime(campaigns["created_at"])
    check("Temporal", "created_at is always at or before start_date",
          (campaigns["created_at"].dt.date <= campaigns["start_date"].dt.date).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "ad_objective values are unique across all 5 campaigns (one campaign per objective)",
          not campaigns["ad_objective"].duplicated().any())
    check("Business rule", "every campaign here is evergreen (no end_date) -- unlike Meta, Search's brand-term "
                          "defense campaign is realistically always-on, not a flighted study",
          campaigns["end_date"].isna().all())

    # --- 5. Distributional sanity ---
    check("Distributional", "all 5 objectives are represented exactly once",
          set(campaigns["ad_objective"]) == {"prospecting", "retargeting", "lookalike", "conversion", "brand_lift"}
          and len(campaigns) == 5)

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
