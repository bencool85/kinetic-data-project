"""
Validation for `youtube_campaigns` (Phase 7, YouTube table 1 of 3) --
pandas-based, 5-layer approach. Same structural class as
validate_meta_campaigns.py (this platform mirrors Meta's flighted-brand_lift
structure, not Search's evergreen one).
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    campaigns = pd.read_csv("../data/youtube_campaigns.csv")

    # --- 1. Structural ---
    check("Structural", "campaign_id non-null and unique",
          campaigns["campaign_id"].notna().all() and campaigns["campaign_id"].is_unique)
    check("Structural", "customer_id, name, ad_objective, advertising_channel_type, video_ad_format, "
                       "bidding_strategy_type, status non-null on every row",
          campaigns[["customer_id", "name", "ad_objective", "advertising_channel_type", "video_ad_format",
                     "bidding_strategy_type", "status"]].notna().all().all())
    check("Structural", "ad_objective is always one of the 5 shared objectives",
          campaigns["ad_objective"].isin(["prospecting", "retargeting", "lookalike", "conversion", "brand_lift"]).all())
    check("Structural", "advertising_channel_type is always VIDEO (this is the YouTube platform table, "
                       "a genuinely different Google Ads product surface than Search)",
          (campaigns["advertising_channel_type"] == "VIDEO").all())
    check("Structural", "video_ad_format is a valid YouTube ad format enum value",
          campaigns["video_ad_format"].isin(["VIDEO_TRUE_VIEW_IN_STREAM", "VIDEO_ACTION", "VIDEO_BUMPER",
                                              "VIDEO_NON_SKIPPABLE_IN_STREAM", "VIDEO_OUTSTREAM"]).all())
    check("Structural", "status is always a valid Google Ads campaign status",
          campaigns["status"].isin(["ENABLED", "PAUSED", "REMOVED"]).all())
    check("Structural", "exactly one budget field (campaign_budget_micros XOR lifetime_budget_micros) is set",
          ((campaigns["campaign_budget_micros"].notna()) ^ (campaigns["lifetime_budget_micros"].notna())).all())

    # --- 2. Referential integrity ---
    check("Referential", "n/a -- this is a root definitions table with no FKs of its own", True)

    # --- 3. Temporal ordering ---
    campaigns["created_at"] = pd.to_datetime(campaigns["created_at"])
    campaigns["start_date"] = pd.to_datetime(campaigns["start_date"])
    check("Temporal", "created_at is always at or before start_date",
          (campaigns["created_at"].dt.date <= campaigns["start_date"].dt.date).all())
    with_end = campaigns[campaigns["end_date"].notna()].copy()
    with_end["end_date"] = pd.to_datetime(with_end["end_date"])
    check("Temporal", "end_date (where set) is always after start_date",
          (with_end["end_date"] > with_end["start_date"]).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "ad_objective is unique among the 4 evergreen campaigns",
          not campaigns.loc[campaigns["ad_objective"] != "brand_lift", "ad_objective"].duplicated().any())
    check("Business rule", "every brand_lift campaign has a lifetime_budget_micros and an end_date (flighted, "
                          "same pattern as Meta -- YouTube Brand Lift is a real flighted measurement product)",
          campaigns.loc[campaigns["ad_objective"] == "brand_lift", "lifetime_budget_micros"].notna().all()
          and campaigns.loc[campaigns["ad_objective"] == "brand_lift", "end_date"].notna().all())
    check("Business rule", "every evergreen campaign has a campaign_budget_micros and no end_date",
          campaigns.loc[campaigns["ad_objective"] != "brand_lift", "campaign_budget_micros"].notna().all()
          and campaigns.loc[campaigns["ad_objective"] != "brand_lift", "end_date"].isna().all())

    # --- 5. Distributional sanity ---
    n_evergreen = (campaigns["ad_objective"] != "brand_lift").sum()
    n_brand_lift = (campaigns["ad_objective"] == "brand_lift").sum()
    check("Distributional", "4 evergreen campaigns + brand_lift flights",
          n_evergreen == 4 and n_brand_lift >= 1, detail=f"{n_evergreen} evergreen / {n_brand_lift} brand_lift")

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
