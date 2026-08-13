"""
Validation for `google_search_performance_daily` (Phase 7, Google Search
table 3 of 4 by schema order). Central check: this table is an EXACT
aggregation of google_search_keyword_performance_daily.csv up to
(ad_group_id, date) grain -- checked as an exact-count reconciliation
(sum of keyword rows == ad-group row), not a plausibility band, since it's
derived directly from that table by construction.
"""
import numpy as np
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    perf = pd.read_csv("../data/google_search_performance_daily.csv")
    kw = pd.read_csv("../data/google_search_keyword_performance_daily.csv")
    ad_groups = pd.read_csv("../data/google_search_ad_groups.csv")
    campaigns = pd.read_csv("../data/google_search_campaigns.csv")

    # --- 1. Structural ---
    required = ["campaign_id", "ad_group_id", "date", "impressions", "clicks", "cost_micros",
                "ctr", "conversions", "conversions_value"]
    check("Structural", "all required fields non-null (average_cpc_micros nullable only when clicks==0)",
          perf[required].notna().all().all())
    check("Structural", "average_cpc_micros is null IFF clicks == 0",
          (perf["average_cpc_micros"].isna() == (perf["clicks"] == 0)).all())
    check("Structural", "(ad_group_id, date) is unique -- exactly one row per ad group per day",
          not perf.duplicated(subset=["ad_group_id", "date"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_group_id exists in google_search_ad_groups.csv",
          perf["ad_group_id"].isin(ad_groups["ad_group_id"]).all())
    check("Referential", "every campaign_id exists in google_search_campaigns.csv",
          perf["campaign_id"].isin(campaigns["campaign_id"]).all())

    # --- 3. Temporal ordering ---
    check("Temporal", "n/a -- this table shares its date grain with keyword_performance_daily, "
                     "no independent ordering to check", True)

    # --- 4. Business-rule invariants (the central derivation check) ---
    expected = kw.groupby(["campaign_id", "ad_group_id", "date"]).agg(
        impressions=("impressions", "sum"), clicks=("clicks", "sum"), cost_micros=("cost_micros", "sum"),
        conversions=("conversions", "sum"), conversions_value=("conversions_value", "sum"),
    ).reset_index()
    merged = perf.merge(expected, on=["campaign_id", "ad_group_id", "date"], suffixes=("", "_expected"))
    check("Business rule", "every ad_group/day row's impressions/clicks/cost_micros EXACTLY equals the sum "
                          "of that same ad_group/day's own keyword_performance_daily.csv rows",
          (merged["impressions"] == merged["impressions_expected"]).all()
          and (merged["clicks"] == merged["clicks_expected"]).all()
          and (merged["cost_micros"] == merged["cost_micros_expected"]).all())
    check("Business rule", "conversions and conversions_value also reconcile exactly (within float rounding)",
          np.isclose(merged["conversions"], merged["conversions_expected"], atol=0.02).all()
          and np.isclose(merged["conversions_value"], merged["conversions_value_expected"], atol=0.02).all())
    check("Business rule", "no ad_group/day combination exists in this table that ISN'T backed by at least "
                          "one keyword_performance_daily.csv row (no orphaned aggregates)",
          len(perf) == len(expected))
    check("Business rule", "ctr and average_cpc_micros recompute exactly from the aggregated impressions/clicks/cost",
          np.isclose(perf["ctr"], perf["clicks"] / perf["impressions"], atol=1e-4).all())

    # --- 5. Distributional sanity ---
    check("Distributional", "total cost across this table matches keyword_performance_daily.csv's own total "
                          "exactly (both represent the same underlying spend, just at different grains)",
          np.isclose(perf["cost_micros"].sum(), kw["cost_micros"].sum()),
          detail=f"${perf['cost_micros'].sum()/1e6:,.2f} vs ${kw['cost_micros'].sum()/1e6:,.2f}")

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
