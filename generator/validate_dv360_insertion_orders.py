"""
Validation for `dv360_insertion_orders` (Phase 7, DV360 table 1 of 3) --
pandas-based, 5-layer approach. Same lightweight definitions-table class
as meta_campaigns.py / google_search_campaigns.py, adapted for DV360's IO
resource fields.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    ios = pd.read_csv("../data/dv360_insertion_orders.csv")

    # --- 1. Structural ---
    check("Structural", "insertion_order_id non-null and unique",
          ios["insertion_order_id"].notna().all() and ios["insertion_order_id"].is_unique)
    check("Structural", "advertiser_id, name, ad_objective, performance_goal_type, pacing_type, budget_type, "
                       "budget_micros, status all non-null",
          ios[["advertiser_id", "name", "ad_objective", "performance_goal_type", "pacing_type",
               "budget_type", "budget_micros", "status"]].notna().all().all())
    check("Structural", "ad_objective is always one of the 5 shared objectives",
          ios["ad_objective"].isin(["prospecting", "retargeting", "lookalike", "conversion", "brand_lift"]).all())
    check("Structural", "performance_goal_type is a valid DV360 PerformanceGoalType enum value",
          ios["performance_goal_type"].isin(["PERFORMANCE_GOAL_TYPE_CPM", "PERFORMANCE_GOAL_TYPE_CPC",
                                              "PERFORMANCE_GOAL_TYPE_CPA", "PERFORMANCE_GOAL_TYPE_VIEWABLE_CPM",
                                              "PERFORMANCE_GOAL_TYPE_CPIAVC"]).all())
    check("Structural", "status is always a valid DV360 EntityStatus enum value",
          ios["status"].isin(["ENTITY_STATUS_ACTIVE", "ENTITY_STATUS_PAUSED", "ENTITY_STATUS_ARCHIVED"]).all())
    check("Structural", "advertiser_id is the SAME single value on every row (one advertiser account "
                       "for this whole dataset, same convention as Meta's single account_id)",
          ios["advertiser_id"].nunique() == 1)

    # --- 2. Referential integrity ---
    check("Referential", "n/a -- this is a root definitions table with no FKs of its own", True)

    # --- 3. Temporal ordering ---
    ios["created_at"] = pd.to_datetime(ios["created_at"])
    ios["start_date"] = pd.to_datetime(ios["start_date"])
    check("Temporal", "created_at is always at or before start_date",
          (ios["created_at"].dt.date <= ios["start_date"].dt.date).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "ad_objective values are unique across all 5 IOs (one IO per objective)",
          not ios["ad_objective"].duplicated().any())
    check("Business rule", "the brand_lift IO's performance_goal_type is VIEWABLE_CPM (an awareness/reach "
                          "goal), not a conversion-oriented goal like the others",
          (ios.loc[ios["ad_objective"] == "brand_lift", "performance_goal_type"]
           == "PERFORMANCE_GOAL_TYPE_VIEWABLE_CPM").all())
    check("Business rule", "every IO is evergreen (no end_date) -- a programmatic reach buy is a continuous "
                          "always-on line item here, not a flighted study",
          ios["end_date"].isna().all())

    # --- 5. Distributional sanity ---
    check("Distributional", "all 5 objectives are represented exactly once",
          set(ios["ad_objective"]) == {"prospecting", "retargeting", "lookalike", "conversion", "brand_lift"}
          and len(ios) == 5)

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
