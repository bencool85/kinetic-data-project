"""
Phase 7 - tiktok_ads table (3 of 4). Creative-level entity, one level
below ad group -- no targeting here (that lives on the ad group), same
pattern as snap_ads.py.

Output: data/tiktok_ads.csv
"""
import datetime
import pandas as pd


def build_tiktok_ads():
    adgroups = pd.read_csv("../data/tiktok_adgroups.csv")
    campaigns = pd.read_csv("../data/tiktok_campaigns.csv")
    adgroups = adgroups.merge(campaigns[["campaign_id", "ad_objective"]], on="campaign_id")

    rows = []
    ad_i = 1

    def add_ad(ag_row, name, ad_format):
        nonlocal ad_i
        rows.append({
            "ad_id": f"175830{ad_i:013d}",
            "adgroup_id": ag_row["adgroup_id"],
            "ad_name": name,
            "ad_format": ad_format,
            "status": ag_row["status"],
            "create_time": (pd.Timestamp(ag_row["create_time"]) + datetime.timedelta(hours=1)).isoformat(),
        })
        ad_i += 1

    for _, ag in adgroups.iterrows():
        obj = ag["ad_objective"]
        if obj == "prospecting":
            add_ad(ag, "Creative A - Single Video", "SINGLE_VIDEO")
            add_ad(ag, "Creative B - Spark Ad", "SPARK_AD")
        elif obj == "retargeting":
            add_ad(ag, "Creative A - Collection", "COLLECTION")
        elif obj == "lookalike":
            add_ad(ag, "Creative A - Single Video", "SINGLE_VIDEO")
        elif obj == "conversion":
            add_ad(ag, "Creative A - Collection", "COLLECTION")
            add_ad(ag, "Creative B - Single Video", "SINGLE_VIDEO")
        elif obj == "brand_lift":
            add_ad(ag, "Creative A - Single Video", "SINGLE_VIDEO")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_tiktok_ads()
    df.to_csv("../data/tiktok_ads.csv", index=False)
    print(f"Wrote {len(df)} tiktok_ads\n")
    print(df.to_string(index=False))
