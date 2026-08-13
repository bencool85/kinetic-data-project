"""
Phase 7 - dv360_line_items table (2 of 3). DV360 line_item resource, one
level below insertion_order. Same targeting_segment_id split as every
other platform: retargeting splits across 2 line items (one per DV360
retargeting segment), lookalike gets 1 targeted line item, everything
else broad.

Output: data/dv360_line_items.csv
"""
import datetime
import pandas as pd

from params import DV360_LINE_ITEM_TYPE_BY_OBJECTIVE


def build_dv360_line_items():
    ios = pd.read_csv("../data/dv360_insertion_orders.csv")
    segments = pd.read_csv("../data/segments.csv")
    dv_segs = segments[segments["ad_platform"] == "dv360"].set_index("segment_name")["segment_id"]
    website_visitors_seg = dv_segs[[n for n in dv_segs.index if n.startswith("Website Visitors")][0]]
    cart_abandoners_seg = dv_segs[[n for n in dv_segs.index if n.startswith("Cart Abandoners")][0]]
    lookalike_seg = dv_segs[[n for n in dv_segs.index if n.startswith("Lookalike")][0]]

    rows = []
    li_i = 1

    def add_line_item(io_row, name, targeting_segment_id):
        nonlocal li_i
        rows.append({
            "line_item_id": f"201{li_i:015d}",
            "insertion_order_id": io_row["insertion_order_id"],
            "name": name,
            "line_item_type": DV360_LINE_ITEM_TYPE_BY_OBJECTIVE[io_row["ad_objective"]],
            "targeting_segment_id": targeting_segment_id,
            "status": "ENTITY_STATUS_ACTIVE",
            "created_at": (pd.Timestamp(io_row["created_at"]) + datetime.timedelta(hours=2)).isoformat(),
        })
        li_i += 1

    for _, io in ios.iterrows():
        obj = io["ad_objective"]
        if obj == "prospecting":
            add_line_item(io, "Open Web Display - Run of Network", None)
        elif obj == "retargeting":
            add_line_item(io, "Retargeting - Website Visitors 30D", website_visitors_seg)
            add_line_item(io, "Retargeting - Cart Abandoners", cart_abandoners_seg)
        elif obj == "lookalike":
            add_line_item(io, "Lookalike - Recent Converters", lookalike_seg)
        elif obj == "conversion":
            add_line_item(io, "Conversion - High-Intent Display", None)
        elif obj == "brand_lift":
            add_line_item(io, "Awareness - Video & Connected TV", None)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_dv360_line_items()
    df.to_csv("../data/dv360_line_items.csv", index=False)
    print(f"Wrote {len(df)} dv360_line_items\n")
    print(df.to_string(index=False))
