"""
Validation for `meta_ads` (Phase 7, Meta table 2 of 4) -- pandas-based,
5-layer approach. Central check: targeting_segment_id is populated ONLY
for retargeting/lookalike ads (never prospecting/conversion/brand_lift),
and always resolves to a real Meta anonymous-grain segment.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    ads = pd.read_csv("../data/meta_ads.csv")
    campaigns = pd.read_csv("../data/meta_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")

    ads = ads.merge(campaigns[["campaign_id", "ad_objective", "created_time"]], on="campaign_id",
                     suffixes=("", "_campaign"))

    # --- 1. Structural ---
    check("Structural", "ad_id non-null and unique",
          ads["ad_id"].notna().all() and ads["ad_id"].is_unique)
    check("Structural", "campaign_id, name, status, optimization_goal, billing_event non-null on every row",
          ads[["campaign_id", "name", "status", "optimization_goal", "billing_event"]].notna().all().all())
    check("Structural", "status is always a valid Meta ad status",
          ads["status"].isin(["ACTIVE", "PAUSED", "ARCHIVED", "COMPLETED"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every campaign_id exists in meta_campaigns.csv",
          ads["campaign_id"].isin(campaigns["campaign_id"]).all())
    anon_segments = set(segments.loc[segments["audience_grain"] == "anonymous_device", "segment_id"])
    meta_segments = set(segments.loc[(segments["audience_grain"] == "anonymous_device")
                                      & (segments["ad_platform"] == "meta"), "segment_id"])
    targeted = ads[ads["targeting_segment_id"].notna()]
    check("Referential", "every non-null targeting_segment_id exists in segments.csv as an "
                        "anonymous-grain segment specifically owned by ad_platform=='meta' "
                        "(never another platform's audience)",
          targeted["targeting_segment_id"].isin(meta_segments).all())

    # --- 3. Temporal ordering ---
    ads["created_time"] = pd.to_datetime(ads["created_time"])
    ads["created_time_campaign"] = pd.to_datetime(ads["created_time_campaign"])
    check("Temporal", "every ad's created_time is at or after its own campaign's created_time",
          (ads["created_time"] >= ads["created_time_campaign"]).all())

    # --- 4. Business-rule invariants ---
    should_target = ads["ad_objective"].isin(["retargeting", "lookalike"])
    check("Business rule", "targeting_segment_id is populated IFF the ad's campaign objective is "
                          "retargeting or lookalike (prospecting/conversion/brand_lift are always broad)",
          (ads["targeting_segment_id"].notna() == should_target).all())
    retargeting_ads = ads[ads["ad_objective"] == "retargeting"]
    check("Business rule", "the 2 retargeting ads under the retargeting campaign target 2 DIFFERENT "
                          "segments (one per real ad-set-style split), not the same segment twice",
          retargeting_ads["targeting_segment_id"].nunique() == len(retargeting_ads))

    # --- 5. Distributional sanity ---
    check("Distributional", "every campaign has at least one ad", set(campaigns["campaign_id"]) == set(ads["campaign_id"]))
    check("Distributional", "ad count per campaign is small and realistic for this dataset's scale (1-3)",
          ads.groupby("campaign_id").size().between(1, 3).all())

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
