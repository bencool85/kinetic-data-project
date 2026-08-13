"""
Validation for `tiktok_ads` (Phase 7, TikTok table 3 of 4) -- pandas-based,
5-layer approach. Creative-level table, same class as validate_snap_ads.py.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    ads = pd.read_csv("../data/tiktok_ads.csv")
    adgroups = pd.read_csv("../data/tiktok_adgroups.csv")

    ads = ads.merge(adgroups[["adgroup_id", "status", "create_time"]], on="adgroup_id", suffixes=("", "_adgroup"))

    # --- 1. Structural ---
    check("Structural", "ad_id non-null and unique", ads["ad_id"].notna().all() and ads["ad_id"].is_unique)
    check("Structural", "adgroup_id, ad_name, ad_format, status non-null on every row",
          ads[["adgroup_id", "ad_name", "ad_format", "status"]].notna().all().all())
    check("Structural", "ad_format is a valid TikTok creative format",
          ads["ad_format"].isin(["SINGLE_VIDEO", "SPARK_AD", "COLLECTION"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every adgroup_id exists in tiktok_adgroups.csv",
          ads["adgroup_id"].isin(adgroups["adgroup_id"]).all())

    # --- 3. Temporal ordering ---
    ads["create_time"] = pd.to_datetime(ads["create_time"])
    ads["create_time_adgroup"] = pd.to_datetime(ads["create_time_adgroup"])
    check("Temporal", "every ad's create_time is at or after its own ad group's create_time",
          (ads["create_time"] >= ads["create_time_adgroup"]).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "an ad's status always matches its own ad group's status "
                          "(a DISABLED flight can't have a still-ENABLED ad under it)",
          (ads["status"] == ads["status_adgroup"]).all())

    # --- 5. Distributional sanity ---
    check("Distributional", "every ad group has at least one ad",
          set(adgroups["adgroup_id"]) == set(ads["adgroup_id"]))
    check("Distributional", "ad count per ad group is small and realistic for this dataset's scale (1-2)",
          ads.groupby("adgroup_id").size().between(1, 2).all())

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
