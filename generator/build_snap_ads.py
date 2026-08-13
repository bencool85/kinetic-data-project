"""
Phase 7 - snap_ads table (3 of 4). Creative-level entity, one level below
ad_squad -- no targeting here (that lives on the ad squad), just creative
variants, mirroring meta_ads.py's 1-2-variants-per-targeting-unit pattern.

Output: data/snap_ads.csv
"""
import datetime
import pandas as pd


def build_snap_ads():
    ad_squads = pd.read_csv("../data/snap_ad_squads.csv")
    campaigns = pd.read_csv("../data/snap_campaigns.csv")
    ad_squads = ad_squads.merge(campaigns[["campaign_id", "ad_objective"]], on="campaign_id")

    rows = []
    ad_i = 1

    def add_ad(squad_row, name, ad_type):
        nonlocal ad_i
        rows.append({
            "ad_id": f"00000000-0000-4000-d000-{ad_i:012d}",
            "ad_squad_id": squad_row["ad_squad_id"],
            "name": name,
            "ad_type": ad_type,
            "status": squad_row["status"],
            "created_at": (pd.Timestamp(squad_row["created_at"]) + datetime.timedelta(hours=1)).isoformat(),
        })
        ad_i += 1

    for _, squad in ad_squads.iterrows():
        obj = squad["ad_objective"]
        if obj == "prospecting":
            add_ad(squad, "Creative A - Vertical Video", "video")
            add_ad(squad, "Creative B - Single Image", "single_image")
        elif obj == "retargeting":
            add_ad(squad, "Creative A - Collection", "collection")
        elif obj == "lookalike":
            add_ad(squad, "Creative A - Single Image", "single_image")
        elif obj == "conversion":
            add_ad(squad, "Creative A - Collection", "collection")
            add_ad(squad, "Creative B - Single Image", "single_image")
        elif obj == "brand_lift":
            add_ad(squad, "Creative A - Vertical Video", "video")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_snap_ads()
    df.to_csv("../data/snap_ads.csv", index=False)
    print(f"Wrote {len(df)} snap_ads\n")
    print(df.to_string(index=False))
