"""
Phase 7 - snap_ad_squads table (2 of 4). Snap's real, explicitly-named
ad-set-level targeting entity -- unlike Meta, Snap's API genuinely has
this as its own object, so (unlike meta_ads.py) targeting_segment_id lives
here, not folded into the creative-level table.

Same split as every other platform: retargeting gets 2 ad squads (one per
Snap retargeting segment), lookalike gets 1, everything else stays broad.

Output: data/snap_ad_squads.csv
"""
import datetime
import pandas as pd


def build_snap_ad_squads():
    campaigns = pd.read_csv("../data/snap_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")
    snap_segs = segments[segments["ad_platform"] == "snap"].set_index("segment_name")["segment_id"]
    website_visitors_seg = snap_segs[[n for n in snap_segs.index if n.startswith("Website Visitors")][0]]
    cart_abandoners_seg = snap_segs[[n for n in snap_segs.index if n.startswith("Cart Abandoners")][0]]
    lookalike_seg = snap_segs[[n for n in snap_segs.index if n.startswith("Lookalike")][0]]

    rows = []
    sq_i = 1

    def add_squad(campaign_row, name, targeting_segment_id):
        nonlocal sq_i
        rows.append({
            "ad_squad_id": f"00000000-0000-4000-c000-{sq_i:012d}",
            "campaign_id": campaign_row["campaign_id"],
            "name": name,
            "status": campaign_row["status"],
            "targeting_segment_id": targeting_segment_id,
            "optimization_goal": "SWIPES" if campaign_row["ad_objective"] == "prospecting"
                                  else ("IMPRESSIONS" if campaign_row["ad_objective"] == "brand_lift"
                                        else "PIXEL_PURCHASE"),
            "created_at": (pd.Timestamp(campaign_row["created_at"]) + datetime.timedelta(hours=2)).isoformat(),
        })
        sq_i += 1

    for _, camp in campaigns.iterrows():
        obj = camp["ad_objective"]
        if obj == "prospecting":
            add_squad(camp, "Prospecting - Broad Snapchatters 18-34", None)
        elif obj == "retargeting":
            add_squad(camp, "Retargeting - Website Visitors 30D", website_visitors_seg)
            add_squad(camp, "Retargeting - Cart Abandoners", cart_abandoners_seg)
        elif obj == "lookalike":
            add_squad(camp, "Lookalike - Recent Converters", lookalike_seg)
        elif obj == "conversion":
            add_squad(camp, "Web Conversions - Core Audience", None)
        elif obj == "brand_lift":
            add_squad(camp, f"Awareness - {camp['name'].split()[-1]} Flight", None)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_snap_ad_squads()
    df.to_csv("../data/snap_ad_squads.csv", index=False)
    print(f"Wrote {len(df)} snap_ad_squads\n")
    print(df.to_string(index=False))
