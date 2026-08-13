"""
Validation for `snap_ad_squads` (Phase 7, Snap table 2 of 4) --
pandas-based, 5-layer approach.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    ad_squads = pd.read_csv("../data/snap_ad_squads.csv")
    campaigns = pd.read_csv("../data/snap_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")

    ad_squads = ad_squads.merge(campaigns[["campaign_id", "ad_objective", "created_at"]], on="campaign_id",
                                 suffixes=("", "_campaign"))

    # --- 1. Structural ---
    check("Structural", "ad_squad_id non-null and unique",
          ad_squads["ad_squad_id"].notna().all() and ad_squads["ad_squad_id"].is_unique)
    check("Structural", "campaign_id, name, status, optimization_goal non-null on every row",
          ad_squads[["campaign_id", "name", "status", "optimization_goal"]].notna().all().all())
    check("Structural", "optimization_goal is a valid Snap ad-squad optimization goal",
          ad_squads["optimization_goal"].isin(["SWIPES", "IMPRESSIONS", "PIXEL_PURCHASE", "VIDEO_VIEWS"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every campaign_id exists in snap_campaigns.csv",
          ad_squads["campaign_id"].isin(campaigns["campaign_id"]).all())
    snap_segments = set(segments.loc[(segments["audience_grain"] == "anonymous_device")
                                      & (segments["ad_platform"] == "snap"), "segment_id"])
    targeted = ad_squads[ad_squads["targeting_segment_id"].notna()]
    check("Referential", "every non-null targeting_segment_id exists in segments.csv as an anonymous-grain "
                        "segment specifically owned by ad_platform=='snap'",
          targeted["targeting_segment_id"].isin(snap_segments).all())

    # --- 3. Temporal ordering ---
    ad_squads["created_at"] = pd.to_datetime(ad_squads["created_at"])
    ad_squads["created_at_campaign"] = pd.to_datetime(ad_squads["created_at_campaign"])
    check("Temporal", "every ad squad's created_at is at or after its own campaign's created_at",
          (ad_squads["created_at"] >= ad_squads["created_at_campaign"]).all())

    # --- 4. Business-rule invariants ---
    should_target = ad_squads["ad_objective"].isin(["retargeting", "lookalike"])
    check("Business rule", "targeting_segment_id is populated IFF the ad squad's campaign objective is "
                          "retargeting or lookalike",
          (ad_squads["targeting_segment_id"].notna() == should_target).all())
    retargeting_squads = ad_squads[ad_squads["ad_objective"] == "retargeting"]
    check("Business rule", "the 2 retargeting ad squads target 2 DIFFERENT segments, not the same one twice",
          retargeting_squads["targeting_segment_id"].nunique() == len(retargeting_squads))
    check("Business rule", "the prospecting ad squad optimizes for SWIPES and brand_lift squads optimize for "
                          "IMPRESSIONS, matching each objective's real optimization intent",
          (ad_squads.loc[ad_squads["ad_objective"] == "prospecting", "optimization_goal"] == "SWIPES").all()
          and (ad_squads.loc[ad_squads["ad_objective"] == "brand_lift", "optimization_goal"] == "IMPRESSIONS").all())

    # --- 5. Distributional sanity ---
    check("Distributional", "every campaign has at least one ad squad",
          set(campaigns["campaign_id"]) == set(ad_squads["campaign_id"]))
    check("Distributional", "ad squad count per campaign is small and realistic for this dataset's scale (1-2)",
          ad_squads.groupby("campaign_id").size().between(1, 2).all())

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
