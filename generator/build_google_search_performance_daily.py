"""
Phase 7 - google_search_performance_daily table (3 of 4 by
schema_reference.md's listed order; built FOURTH, aggregating UP from
google_search_keyword_performance_daily.csv's own keyword-level rows --
same "derive the coarser table from an already-shipped finer one" pattern
used throughout this project, guaranteeing this table's ad_group/day
totals equal the exact sum of that ad group's keyword rows for that day,
by construction (checked exactly in the validator, not just plausibly).

cost_micros, per schema_reference.md's own callout for this table.

Output: data/google_search_performance_daily.csv
"""
import pandas as pd


def build_google_search_performance_daily():
    kw = pd.read_csv("../data/google_search_keyword_performance_daily.csv")

    grouped = kw.groupby(["campaign_id", "ad_group_id", "date"]).agg(
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        cost_micros=("cost_micros", "sum"),
        conversions=("conversions", "sum"),
        conversions_value=("conversions_value", "sum"),
    ).reset_index()

    grouped["ctr"] = (grouped["clicks"] / grouped["impressions"]).round(6)
    grouped["average_cpc_micros"] = grouped.apply(
        lambda r: int(round(r["cost_micros"] / r["clicks"])) if r["clicks"] > 0 else None, axis=1)
    grouped["conversions"] = grouped["conversions"].round(2)
    grouped["conversions_value"] = grouped["conversions_value"].round(2)

    grouped = grouped.sort_values(["date", "ad_group_id"]).reset_index(drop=True)
    cols = ["campaign_id", "ad_group_id", "date", "impressions", "clicks", "cost_micros",
            "average_cpc_micros", "ctr", "conversions", "conversions_value"]
    return grouped[cols]


if __name__ == "__main__":
    df = build_google_search_performance_daily()
    df.to_csv("../data/google_search_performance_daily.csv", index=False)
    print(f"Wrote {len(df)} google_search_performance_daily rows\n")
    print(f"Total cost: ${df['cost_micros'].sum() / 1_000_000:,.2f}")
    print(f"Total clicks: {df['clicks'].sum():,}")
