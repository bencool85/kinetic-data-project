"""
Validation for `google_search_ad_groups` (Phase 7, Google Search table 2
of 4) -- pandas-based, 5-layer approach. Same targeting_segment_id
discipline check as validate_meta_ads.py.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    ad_groups = pd.read_csv("../data/google_search_ad_groups.csv")
    campaigns = pd.read_csv("../data/google_search_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")

    ad_groups = ad_groups.merge(campaigns[["campaign_id", "ad_objective", "created_at"]], on="campaign_id",
                                 suffixes=("", "_campaign"))

    # --- 1. Structural ---
    check("Structural", "ad_group_id non-null and unique",
          ad_groups["ad_group_id"].notna().all() and ad_groups["ad_group_id"].is_unique)
    check("Structural", "campaign_id, name, status non-null on every row",
          ad_groups[["campaign_id", "name", "status"]].notna().all().all())
    check("Structural", "status is always a valid Google Ads ad_group status",
          ad_groups["status"].isin(["ENABLED", "PAUSED", "REMOVED"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every campaign_id exists in google_search_campaigns.csv",
          ad_groups["campaign_id"].isin(campaigns["campaign_id"]).all())
    gs_segments = set(segments.loc[(segments["audience_grain"] == "anonymous_device")
                                    & (segments["ad_platform"] == "google_search"), "segment_id"])
    targeted = ad_groups[ad_groups["targeting_segment_id"].notna()]
    check("Referential", "every non-null targeting_segment_id exists in segments.csv as an anonymous-grain "
                        "segment specifically owned by ad_platform=='google_search'",
          targeted["targeting_segment_id"].isin(gs_segments).all())

    # --- 3. Temporal ordering ---
    ad_groups["created_at"] = pd.to_datetime(ad_groups["created_at"])
    ad_groups["created_at_campaign"] = pd.to_datetime(ad_groups["created_at_campaign"])
    check("Temporal", "every ad group's created_at is at or after its own campaign's created_at",
          (ad_groups["created_at"] >= ad_groups["created_at_campaign"]).all())

    # --- 4. Business-rule invariants ---
    should_target = ad_groups["ad_objective"].isin(["retargeting", "lookalike"])
    check("Business rule", "targeting_segment_id is populated IFF the ad group's campaign objective is "
                          "retargeting or lookalike",
          (ad_groups["targeting_segment_id"].notna() == should_target).all())
    retargeting_ags = ad_groups[ad_groups["ad_objective"] == "retargeting"]
    check("Business rule", "the 2 RLSA ad groups target 2 DIFFERENT segments, not the same one twice",
          retargeting_ags["targeting_segment_id"].nunique() == len(retargeting_ags))

    # --- 5. Distributional sanity ---
    check("Distributional", "every campaign has at least one ad group",
          set(campaigns["campaign_id"]) == set(ad_groups["campaign_id"]))
    check("Distributional", "ad group count per campaign is small and realistic for this dataset's scale (1-2)",
          ad_groups.groupby("campaign_id").size().between(1, 2).all())

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
