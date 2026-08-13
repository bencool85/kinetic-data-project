"""
Validation for `dv360_line_items` (Phase 7, DV360 table 2 of 3) --
pandas-based, 5-layer approach. Same targeting_segment_id discipline
check as every other platform's ad-set-level table.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    line_items = pd.read_csv("../data/dv360_line_items.csv")
    ios = pd.read_csv("../data/dv360_insertion_orders.csv")
    segments = pd.read_csv("../data/segments.csv")

    line_items = line_items.merge(ios[["insertion_order_id", "ad_objective", "created_at"]],
                                   on="insertion_order_id", suffixes=("", "_io"))

    # --- 1. Structural ---
    check("Structural", "line_item_id non-null and unique",
          line_items["line_item_id"].notna().all() and line_items["line_item_id"].is_unique)
    check("Structural", "insertion_order_id, name, line_item_type, status non-null on every row",
          line_items[["insertion_order_id", "name", "line_item_type", "status"]].notna().all().all())
    check("Structural", "line_item_type is a valid DV360 LineItemType enum value",
          line_items["line_item_type"].isin(["LINE_ITEM_TYPE_DISPLAY_DEFAULT", "LINE_ITEM_TYPE_VIDEO_DEFAULT"]).all())
    check("Structural", "status is a valid DV360 EntityStatus enum value",
          line_items["status"].isin(["ENTITY_STATUS_ACTIVE", "ENTITY_STATUS_PAUSED", "ENTITY_STATUS_ARCHIVED"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every insertion_order_id exists in dv360_insertion_orders.csv",
          line_items["insertion_order_id"].isin(ios["insertion_order_id"]).all())
    dv_segments = set(segments.loc[(segments["audience_grain"] == "anonymous_device")
                                    & (segments["ad_platform"] == "dv360"), "segment_id"])
    targeted = line_items[line_items["targeting_segment_id"].notna()]
    check("Referential", "every non-null targeting_segment_id exists in segments.csv as an anonymous-grain "
                        "segment specifically owned by ad_platform=='dv360'",
          targeted["targeting_segment_id"].isin(dv_segments).all())

    # --- 3. Temporal ordering ---
    line_items["created_at"] = pd.to_datetime(line_items["created_at"])
    line_items["created_at_io"] = pd.to_datetime(line_items["created_at_io"])
    check("Temporal", "every line item's created_at is at or after its own IO's created_at",
          (line_items["created_at"] >= line_items["created_at_io"]).all())

    # --- 4. Business-rule invariants ---
    should_target = line_items["ad_objective"].isin(["retargeting", "lookalike"])
    check("Business rule", "targeting_segment_id is populated IFF the line item's IO objective is "
                          "retargeting or lookalike",
          (line_items["targeting_segment_id"].notna() == should_target).all())
    check("Business rule", "the brand_lift IO's line item is VIDEO type; every other IO's line items are DISPLAY",
          (line_items.loc[line_items["ad_objective"] == "brand_lift", "line_item_type"]
           == "LINE_ITEM_TYPE_VIDEO_DEFAULT").all()
          and (line_items.loc[line_items["ad_objective"] != "brand_lift", "line_item_type"]
               == "LINE_ITEM_TYPE_DISPLAY_DEFAULT").all())
    retargeting_lis = line_items[line_items["ad_objective"] == "retargeting"]
    check("Business rule", "the 2 retargeting line items target 2 DIFFERENT segments, not the same one twice",
          retargeting_lis["targeting_segment_id"].nunique() == len(retargeting_lis))

    # --- 5. Distributional sanity ---
    check("Distributional", "every IO has at least one line item",
          set(ios["insertion_order_id"]) == set(line_items["insertion_order_id"]))
    check("Distributional", "line item count per IO is small and realistic for this dataset's scale (1-2)",
          line_items.groupby("insertion_order_id").size().between(1, 2).all())

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
