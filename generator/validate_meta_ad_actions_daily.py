"""
Validation for `meta_ad_actions_daily` (Phase 7, Meta table 4 of 4 --
completes Meta). Central checks: this table's own click-derived funnel is
internally monotonic (link_click >= landing_page_view >= add_to_cart >=
initiate_checkout >= purchase, by construction since it's derived
directly from meta_ad_insights_daily.csv's own clicks column), link_click
never exceeds that same (ad_id, date)'s own insights row clicks, and the
summed self-attributed "purchase" actions land within a believable
multiple of the business's actual total real purchases (not reconciled
1:1 -- no user-level join exists between ad platforms and our own data,
per schema_reference.md -- but not absurdly divorced from reality either).
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    actions = pd.read_csv("../data/meta_ad_actions_daily.csv")
    insights = pd.read_csv("../data/meta_ad_insights_daily.csv")
    ads = pd.read_csv("../data/meta_ads.csv")
    orders = pd.read_csv("../data/orders.csv")
    subs = pd.read_csv("../data/subscriptions.csv")

    # --- 1. Structural ---
    check("Structural", "ad_id, campaign_id, date, action_type, value all non-null",
          actions.notna().all().all())
    valid_types = {"link_click", "landing_page_view", "add_to_cart", "initiate_checkout", "purchase", "video_view"}
    check("Structural", "action_type is always one of the known Meta action-type vocabulary",
          actions["action_type"].isin(valid_types).all())
    check("Structural", "value is always a positive integer (Meta's actions array omits zero-count "
                       "action types entirely rather than emitting a zero row)",
          (actions["value"] > 0).all() and (actions["value"] == actions["value"].astype(int)).all())
    check("Structural", "(ad_id, date, action_type) is unique -- no duplicate action rows",
          not actions.duplicated(subset=["ad_id", "date", "action_type"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_id exists in meta_ads.csv", actions["ad_id"].isin(ads["ad_id"]).all())
    check("Referential", "every (ad_id, date) pair in actions has a matching row in meta_ad_insights_daily.csv "
                        "(actions can't exist for a day the ad had no reported delivery)",
          actions.set_index(["ad_id", "date"]).index.isin(
              insights.set_index(["ad_id", "date"]).index).all())

    # --- 3. Temporal ordering ---
    check("Temporal", "n/a -- actions share the same date grain as their insights row, no independent "
                     "timestamp ordering to check here", True)

    # --- 4. Business-rule invariants (the central derivation checks) ---
    pivot = actions.pivot_table(index=["ad_id", "date"], columns="action_type", values="value", fill_value=0)
    ins_idx = insights.set_index(["ad_id", "date"])["clicks"]
    pivot = pivot.join(ins_idx, how="left")
    check("Business rule", "link_click never exceeds that same (ad_id, date)'s own insights row's clicks",
          (pivot.get("link_click", 0) <= pivot["clicks"]).all())
    check("Business rule", "the click-derived funnel is monotonically non-increasing at every stage: "
                          "link_click >= landing_page_view >= add_to_cart >= initiate_checkout >= purchase",
          (pivot.get("link_click", 0) >= pivot.get("landing_page_view", 0)).all()
          and (pivot.get("landing_page_view", 0) >= pivot.get("add_to_cart", 0)).all()
          and (pivot.get("add_to_cart", 0) >= pivot.get("initiate_checkout", 0)).all()
          and (pivot.get("initiate_checkout", 0) >= pivot.get("purchase", 0)).all())
    ads_by_obj = ads.merge(pd.read_csv("../data/meta_campaigns.csv")[["campaign_id", "ad_objective"]],
                            on="campaign_id")
    video_ads = set(ads_by_obj.loc[ads_by_obj["ad_objective"].isin(["prospecting", "brand_lift"]), "ad_id"])
    non_video_ads = set(ads_by_obj["ad_id"]) - video_ads
    check("Business rule", "video_view is reported ONLY for prospecting/brand_lift ads (the video-forward "
                          "objectives) -- never for retargeting/lookalike/conversion",
          set(actions.loc[actions["action_type"] == "video_view", "ad_id"]).issubset(video_ads))

    # --- 5. Distributional sanity ---
    total_meta_purchases = actions.loc[actions["action_type"] == "purchase", "value"].sum()
    total_real_purchases = len(orders) + len(subs[subs["trial_start"].isna()
                                                   | (subs["start_date"] != subs["trial_start"])])
    ratio = total_meta_purchases / total_real_purchases
    check("Distributional", "Meta's own self-attributed 'purchase' action total is within a believable "
                          "over-attribution multiple of the business's actual total real purchases "
                          "(0.2x-3x for a SINGLE platform -- real ad platforms over-claim vs. site truth, "
                          "but not by 10-20x per platform, or summing 6 platforms would be absurd)",
          0.2 <= ratio <= 3.0, detail=f"{total_meta_purchases} meta-claimed vs. {total_real_purchases} real "
                                       f"(ratio {ratio:.2f}x)")
    click_to_purchase = total_meta_purchases / actions.loc[actions["action_type"] == "link_click", "value"].sum()
    check("Distributional", "blended click-to-purchase rate across all Meta ads is in a plausible "
                          "e-commerce range (0.3%-5%)",
          0.003 <= click_to_purchase <= 0.05, detail=f"{click_to_purchase:.2%}")

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
