"""
Phase 7 - youtube_ad_groups table (2 of 3). Google Ads ad_group resource,
one level below campaign. Same ad-set-style targeting split as
meta_ads.py: retargeting splits across 2 ad groups (one per YouTube
retargeting segment), lookalike gets 1 targeted ad group, everything else
stays broad.

Output: data/youtube_ad_groups.csv
"""
import datetime
import pandas as pd


def build_youtube_ad_groups():
    campaigns = pd.read_csv("../data/youtube_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")
    yt_segs = segments[segments["ad_platform"] == "youtube"].set_index("segment_name")["segment_id"]
    website_visitors_seg = yt_segs[[n for n in yt_segs.index if n.startswith("Website Visitors")][0]]
    cart_abandoners_seg = yt_segs[[n for n in yt_segs.index if n.startswith("Cart Abandoners")][0]]
    lookalike_seg = yt_segs[[n for n in yt_segs.index if n.startswith("Lookalike")][0]]

    rows = []
    ag_i = 1

    def add_ad_group(campaign_row, name, targeting_segment_id):
        nonlocal ag_i
        rows.append({
            "ad_group_id": f"192{ag_i:015d}",
            "campaign_id": campaign_row["campaign_id"],
            "name": name,
            "status": "REMOVED" if campaign_row["status"] == "REMOVED" else "ENABLED",
            "targeting_segment_id": targeting_segment_id,
            "created_at": (pd.Timestamp(campaign_row["created_at"]) + datetime.timedelta(hours=2)).isoformat(),
        })
        ag_i += 1

    for _, camp in campaigns.iterrows():
        obj = camp["ad_objective"]
        if obj == "prospecting":
            add_ad_group(camp, "Prospecting - 15s Skippable", None)
            add_ad_group(camp, "Prospecting - 30s Skippable", None)
        elif obj == "retargeting":
            add_ad_group(camp, "Video Action - Website Visitors 30D", website_visitors_seg)
            add_ad_group(camp, "Video Action - Cart Abandoners", cart_abandoners_seg)
        elif obj == "lookalike":
            add_ad_group(camp, "TrueView - Similar to Recent Converters", lookalike_seg)
        elif obj == "conversion":
            add_ad_group(camp, "Video Action - Core Audience", None)
        elif obj == "brand_lift":
            add_ad_group(camp, f"Bumper - {camp['name'].split()[-1]} Flight", None)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_youtube_ad_groups()
    df.to_csv("../data/youtube_ad_groups.csv", index=False)
    print(f"Wrote {len(df)} youtube_ad_groups\n")
    print(df.to_string(index=False))
