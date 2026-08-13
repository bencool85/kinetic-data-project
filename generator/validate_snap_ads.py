"""
Validation for `snap_ads` (Phase 7, Snap table 3 of 4) -- pandas-based,
5-layer approach. Creative-level table -- no targeting to check here
(that's snap_ad_squads.py's job), just referential/status consistency.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    ads = pd.read_csv("../data/snap_ads.csv")
    ad_squads = pd.read_csv("../data/snap_ad_squads.csv")

    ads = ads.merge(ad_squads[["ad_squad_id", "status", "created_at"]], on="ad_squad_id",
                     suffixes=("", "_squad"))

    # --- 1. Structural ---
    check("Structural", "ad_id non-null and unique", ads["ad_id"].notna().all() and ads["ad_id"].is_unique)
    check("Structural", "ad_squad_id, name, ad_type, status non-null on every row",
          ads[["ad_squad_id", "name", "ad_type", "status"]].notna().all().all())
    check("Structural", "ad_type is a valid Snap creative type", ads["ad_type"].isin(["single_image", "video", "collection"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_squad_id exists in snap_ad_squads.csv",
          ads["ad_squad_id"].isin(ad_squads["ad_squad_id"]).all())

    # --- 3. Temporal ordering ---
    ads["created_at"] = pd.to_datetime(ads["created_at"])
    ads["created_at_squad"] = pd.to_datetime(ads["created_at_squad"])
    check("Temporal", "every ad's created_at is at or after its own ad squad's created_at",
          (ads["created_at"] >= ads["created_at_squad"]).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "an ad's status always matches its own ad squad's status "
                          "(a COMPLETED flight can't have a still-ACTIVE ad under it)",
          (ads["status"] == ads["status_squad"]).all())
    check("Business rule", "brand_lift ad squads' creative is always video (matches the awareness objective)",
          (ads.merge(ad_squads.merge(pd.read_csv("../data/snap_campaigns.csv")[["campaign_id", "ad_objective"]],
                                      on="campaign_id")[["ad_squad_id", "ad_objective"]], on="ad_squad_id")
           .pipe(lambda d: (d.loc[d["ad_objective"] == "brand_lift", "ad_type"] == "video").all())))

    # --- 5. Distributional sanity ---
    check("Distributional", "every ad squad has at least one ad",
          set(ad_squads["ad_squad_id"]) == set(ads["ad_squad_id"]))
    check("Distributional", "ad count per ad squad is small and realistic for this dataset's scale (1-2)",
          ads.groupby("ad_squad_id").size().between(1, 2).all())

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
