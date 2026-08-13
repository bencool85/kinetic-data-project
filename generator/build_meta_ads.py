"""
Phase 7 - meta_ads table (2 of 4). Functions as the ad-set-level entity
(targeting, optimization_goal) one level below campaign, per
meta_campaigns.py's docstring on why there's no separate ad_sets table.

Ad count per campaign is deliberately small (10 total) -- this is a
100-customer-scale dataset, and a handful of creative variants per
campaign is realistic without inflating the daily-performance tables into
an unreadable size.

- Prospecting: 2 ads (creative A/B), no targeting_segment_id (broad).
- Retargeting: 2 ads, EACH pinned to a different one of segments.csv's two
  retargeting concepts for Meta (seg_010 "Website Visitors - Last 30 Days"
  and seg_016 "Cart Abandoners") -- this is what a real ad set structure
  under a single retargeting campaign looks like.
- Lookalike: 1 ad, targeting_segment_id = seg_022 ("Lookalike - Recent
  Converters - Meta").
- Conversion: 2 ads (creative A/B), no targeting_segment_id.
- Each brand_lift flight: 1 ad, no targeting_segment_id (broad awareness).

Output: data/meta_ads.csv
"""
import datetime
import pandas as pd

OPTIMIZATION_GOAL_BY_OBJECTIVE = {
    "prospecting": "LINK_CLICKS", "retargeting": "OFFSITE_CONVERSIONS", "lookalike": "OFFSITE_CONVERSIONS",
    "conversion": "OFFSITE_CONVERSIONS", "brand_lift": "REACH",
}
BILLING_EVENT_BY_OBJECTIVE = {
    "prospecting": "IMPRESSIONS", "retargeting": "IMPRESSIONS", "lookalike": "IMPRESSIONS",
    "conversion": "IMPRESSIONS", "brand_lift": "IMPRESSIONS",
}


def build_meta_ads():
    campaigns = pd.read_csv("../data/meta_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")
    meta_segs = segments[segments["ad_platform"] == "meta"].set_index("segment_name")["segment_id"]
    website_visitors_seg = meta_segs[[n for n in meta_segs.index if n.startswith("Website Visitors")][0]]
    cart_abandoners_seg = meta_segs[[n for n in meta_segs.index if n.startswith("Cart Abandoners")][0]]
    lookalike_seg = meta_segs[[n for n in meta_segs.index if n.startswith("Lookalike")][0]]

    rows = []
    ad_i = 1

    def add_ad(campaign_row, name, targeting_segment_id):
        nonlocal ad_i
        created = pd.Timestamp(campaign_row["created_time"]) + datetime.timedelta(hours=2)
        rows.append({
            "ad_id": f"238600{ad_i:012d}",
            "campaign_id": campaign_row["campaign_id"],
            "name": name,
            "status": campaign_row["status"] if campaign_row["status"] != "COMPLETED" else "COMPLETED",
            "targeting_segment_id": targeting_segment_id,
            "optimization_goal": OPTIMIZATION_GOAL_BY_OBJECTIVE[campaign_row["ad_objective"]],
            "billing_event": BILLING_EVENT_BY_OBJECTIVE[campaign_row["ad_objective"]],
            "created_time": created.isoformat(),
            "updated_time": campaign_row["updated_time"],
        })
        ad_i += 1

    for _, camp in campaigns.iterrows():
        obj = camp["ad_objective"]
        if obj == "prospecting":
            add_ad(camp, "Prospecting - Creative A - Carousel", None)
            add_ad(camp, "Prospecting - Creative B - Video", None)
        elif obj == "retargeting":
            add_ad(camp, "Retargeting - Website Visitors 30D", website_visitors_seg)
            add_ad(camp, "Retargeting - Cart Abandoners", cart_abandoners_seg)
        elif obj == "lookalike":
            add_ad(camp, "Lookalike 1% - Recent Converters", lookalike_seg)
        elif obj == "conversion":
            add_ad(camp, "Conversion - Creative A - Single Image", None)
            add_ad(camp, "Conversion - Creative B - Carousel", None)
        elif obj == "brand_lift":
            add_ad(camp, f"Brand Lift - {camp['name'].split()[-1]} Flight", None)

    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    df = build_meta_ads()
    df.to_csv("../data/meta_ads.csv", index=False)
    print(f"Wrote {len(df)} meta_ads\n")
    print(df.to_string(index=False))
