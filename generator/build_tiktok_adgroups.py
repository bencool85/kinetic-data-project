"""
Phase 7 - tiktok_adgroups table (2 of 4). TikTok's real ad-set-level
targeting entity, one level below campaign -- same explicit-own-table
treatment as snap_ad_squads.py. Same targeting split as every other
platform: retargeting gets 2 ad groups (one per TikTok retargeting
segment), lookalike gets 1, everything else stays broad.

Output: data/tiktok_adgroups.csv
"""
import datetime
import pandas as pd


def build_tiktok_adgroups():
    campaigns = pd.read_csv("../data/tiktok_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")
    tt_segs = segments[segments["ad_platform"] == "tiktok"].set_index("segment_name")["segment_id"]
    website_visitors_seg = tt_segs[[n for n in tt_segs.index if n.startswith("Website Visitors")][0]]
    cart_abandoners_seg = tt_segs[[n for n in tt_segs.index if n.startswith("Cart Abandoners")][0]]
    lookalike_seg = tt_segs[[n for n in tt_segs.index if n.startswith("Lookalike")][0]]

    rows = []
    ag_i = 1

    def add_adgroup(campaign_row, name, targeting_segment_id):
        nonlocal ag_i
        rows.append({
            "adgroup_id": f"175829{ag_i:013d}",
            "campaign_id": campaign_row["campaign_id"],
            "adgroup_name": name,
            "status": campaign_row["status"],
            "targeting_segment_id": targeting_segment_id,
            "billing_event": "OCPM",
            "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
            "create_time": (pd.Timestamp(campaign_row["create_time"]) + datetime.timedelta(hours=2)).isoformat(),
        })
        ag_i += 1

    for _, camp in campaigns.iterrows():
        obj = camp["ad_objective"]
        if obj == "prospecting":
            add_adgroup(camp, "Prospecting - Broad FYP Placement", None)
        elif obj == "retargeting":
            add_adgroup(camp, "Retargeting - Website Visitors 30D", website_visitors_seg)
            add_adgroup(camp, "Retargeting - Cart Abandoners", cart_abandoners_seg)
        elif obj == "lookalike":
            add_adgroup(camp, "Lookalike - Recent Converters", lookalike_seg)
        elif obj == "conversion":
            add_adgroup(camp, "Conversions - Core Audience", None)
        elif obj == "brand_lift":
            add_adgroup(camp, f"Reach - {camp['campaign_name'].split()[-1]} Flight", None)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_tiktok_adgroups()
    df.to_csv("../data/tiktok_adgroups.csv", index=False)
    print(f"Wrote {len(df)} tiktok_adgroups\n")
    print(df.to_string(index=False))
