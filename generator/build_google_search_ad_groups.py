"""
Phase 7 - google_search_ad_groups table (2 of 4). Google Ads API-shaped
ad_group resource, one level below campaign, grouped by keyword theme.

- Prospecting: 2 ad groups (Generic Fitness Terms, Competitor Comparison
  Terms), no targeting_segment_id.
- Retargeting: 2 ad groups, one per Google Search RLSA segment
  (seg_011 "Website Visitors" and seg_017 "Cart Abandoners").
- Lookalike: 1 ad group, targeting_segment_id = seg_023 (Similar
  Audiences - Recent Converters).
- Conversion: 2 ad groups (Branded Terms, High-Intent Transactional
  Terms), no targeting_segment_id.
- Brand lift (brand defense): 1 ad group (Brand Terms), no
  targeting_segment_id.

Output: data/google_search_ad_groups.csv
"""
import datetime
import pandas as pd


def build_google_search_ad_groups():
    campaigns = pd.read_csv("../data/google_search_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")
    gs_segs = segments[segments["ad_platform"] == "google_search"].set_index("segment_name")["segment_id"]
    website_visitors_seg = gs_segs[[n for n in gs_segs.index if n.startswith("Website Visitors")][0]]
    cart_abandoners_seg = gs_segs[[n for n in gs_segs.index if n.startswith("Cart Abandoners")][0]]
    lookalike_seg = gs_segs[[n for n in gs_segs.index if n.startswith("Lookalike")][0]]

    rows = []
    ag_i = 1

    def add_ad_group(campaign_row, name, targeting_segment_id):
        nonlocal ag_i
        rows.append({
            "ad_group_id": f"180{ag_i:015d}",
            "campaign_id": campaign_row["campaign_id"],
            "name": name,
            "status": "ENABLED",
            "targeting_segment_id": targeting_segment_id,
            "cpc_bid_micros": None,  # bidding is at the TARGET_CPA/MAXIMIZE_CLICKS strategy level for these campaigns
            "created_at": (pd.Timestamp(campaign_row["created_at"]) + datetime.timedelta(hours=2)).isoformat(),
        })
        ag_i += 1

    for _, camp in campaigns.iterrows():
        obj = camp["ad_objective"]
        if obj == "prospecting":
            add_ad_group(camp, "Generic Fitness Terms", None)
            add_ad_group(camp, "Competitor Comparison Terms", None)
        elif obj == "retargeting":
            add_ad_group(camp, "RLSA - Website Visitors 30D", website_visitors_seg)
            add_ad_group(camp, "RLSA - Cart Abandoners", cart_abandoners_seg)
        elif obj == "lookalike":
            add_ad_group(camp, "Similar Audiences - Recent Converters", lookalike_seg)
        elif obj == "conversion":
            add_ad_group(camp, "Branded Terms", None)
            add_ad_group(camp, "High-Intent Transactional Terms", None)
        elif obj == "brand_lift":
            add_ad_group(camp, "Brand Terms Defense", None)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_google_search_ad_groups()
    df.to_csv("../data/google_search_ad_groups.csv", index=False)
    print(f"Wrote {len(df)} google_search_ad_groups\n")
    print(df.to_string(index=False))
