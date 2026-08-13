"""
Validation for `tiktok_adgroups` (Phase 7, TikTok table 2 of 4) --
pandas-based, 5-layer approach.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    adgroups = pd.read_csv("../data/tiktok_adgroups.csv")
    campaigns = pd.read_csv("../data/tiktok_campaigns.csv")
    segments = pd.read_csv("../data/segments.csv")

    adgroups = adgroups.merge(campaigns[["campaign_id", "ad_objective", "create_time"]], on="campaign_id",
                               suffixes=("", "_campaign"))

    # --- 1. Structural ---
    check("Structural", "adgroup_id non-null and unique",
          adgroups["adgroup_id"].notna().all() and adgroups["adgroup_id"].is_unique)
    check("Structural", "campaign_id, adgroup_name, status, billing_event, placement_type non-null on every row",
          adgroups[["campaign_id", "adgroup_name", "status", "billing_event", "placement_type"]].notna().all().all())
    check("Structural", "billing_event is a valid TikTok billing event enum value",
          adgroups["billing_event"].isin(["OCPM", "CPC", "CPM"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every campaign_id exists in tiktok_campaigns.csv",
          adgroups["campaign_id"].isin(campaigns["campaign_id"]).all())
    tt_segments = set(segments.loc[(segments["audience_grain"] == "anonymous_device")
                                    & (segments["ad_platform"] == "tiktok"), "segment_id"])
    targeted = adgroups[adgroups["targeting_segment_id"].notna()]
    check("Referential", "every non-null targeting_segment_id exists in segments.csv as an anonymous-grain "
                        "segment specifically owned by ad_platform=='tiktok'",
          targeted["targeting_segment_id"].isin(tt_segments).all())

    # --- 3. Temporal ordering ---
    adgroups["create_time"] = pd.to_datetime(adgroups["create_time"])
    adgroups["create_time_campaign"] = pd.to_datetime(adgroups["create_time_campaign"])
    check("Temporal", "every ad group's create_time is at or after its own campaign's create_time",
          (adgroups["create_time"] >= adgroups["create_time_campaign"]).all())

    # --- 4. Business-rule invariants ---
    should_target = adgroups["ad_objective"].isin(["retargeting", "lookalike"])
    check("Business rule", "targeting_segment_id is populated IFF the ad group's campaign objective is "
                          "retargeting or lookalike",
          (adgroups["targeting_segment_id"].notna() == should_target).all())
    retargeting_ags = adgroups[adgroups["ad_objective"] == "retargeting"]
    check("Business rule", "the 2 retargeting ad groups target 2 DIFFERENT segments, not the same one twice",
          retargeting_ags["targeting_segment_id"].nunique() == len(retargeting_ags))
    campaign_status = campaigns.set_index("campaign_id")["status"]
    check("Business rule", "an ad group's status is DISABLE whenever its own campaign's status is DISABLE",
          ((adgroups["campaign_id"].map(campaign_status) != "CAMPAIGN_STATUS_DISABLE")
           | (adgroups["status"] == "CAMPAIGN_STATUS_DISABLE")).all())

    # --- 5. Distributional sanity ---
    check("Distributional", "every campaign has at least one ad group",
          set(campaigns["campaign_id"]) == set(adgroups["campaign_id"]))
    check("Distributional", "ad group count per campaign is small and realistic for this dataset's scale (1-2)",
          adgroups.groupby("campaign_id").size().between(1, 2).all())

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
