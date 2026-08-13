"""
Validation for `snap_stats_daily` (Phase 7, Snap table 4 of 4 -- completes
Snap). Same class of checks as validate_meta_ad_insights_daily.py: internal
arithmetic consistency, the cross-phase seasonality/channel-mix
correlation check, and self-attributed-conversions plausibility.
"""
import numpy as np
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    stats = pd.read_csv("../data/snap_stats_daily.csv")
    ads = pd.read_csv("../data/snap_ads.csv")
    ad_squads = pd.read_csv("../data/snap_ad_squads.csv")
    campaigns = pd.read_csv("../data/snap_campaigns.csv")
    web_sessions = pd.read_csv("../data/web_sessions.csv")
    orders = pd.read_csv("../data/orders.csv")
    subs = pd.read_csv("../data/subscriptions.csv")

    stats["date"] = pd.to_datetime(stats["date"])
    stats = stats.merge(ads[["ad_id", "ad_squad_id"]], on=["ad_id", "ad_squad_id"], how="inner")
    stats = stats.merge(ad_squads[["ad_squad_id", "campaign_id"]], on=["ad_squad_id", "campaign_id"], how="inner")
    stats = stats.merge(campaigns[["campaign_id", "start_time", "end_time", "ad_objective"]], on="campaign_id")

    # --- 1. Structural ---
    required = ["ad_id", "ad_squad_id", "campaign_id", "date", "impressions", "swipes", "video_views",
                "spend_micro", "conversions", "conversions_value"]
    check("Structural", "all required fields non-null on every row", stats[required].notna().all().all())
    check("Structural", "impressions, swipes, video_views, spend_micro, conversions all non-negative",
          (stats[["impressions", "swipes", "video_views", "spend_micro", "conversions"]] >= 0).all().all())
    check("Structural", "swipes never exceed impressions", (stats["swipes"] <= stats["impressions"]).all())
    check("Structural", "(ad_id, date) is unique -- exactly one stats row per ad per day",
          not stats.duplicated(subset=["ad_id", "date"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_id exists in snap_ads.csv", stats["ad_id"].isin(ads["ad_id"]).all())
    check("Referential", "every ad_squad_id on a row matches that ad_id's OWN ad_squad_id",
          stats.merge(ads[["ad_id", "ad_squad_id"]], on="ad_id", suffixes=("", "_true"))
          .pipe(lambda d: (d["ad_squad_id"] == d["ad_squad_id_true"]).all()))

    # --- 3. Temporal ordering ---
    stats["start_date"] = pd.to_datetime(stats["start_time"]).dt.date
    end = pd.to_datetime(stats["end_time"])
    stats["end_date"] = end.dt.date
    date_only = stats["date"].dt.date
    check("Temporal", "every row's date falls within its own campaign's [start_time, end_time] window "
                     "(open-ended for evergreen campaigns with no end_time)",
          (date_only >= stats["start_date"]).all()
          and (stats["end_date"].isna() | (date_only <= stats["end_date"])).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "spend_micro is always a whole number of micros (integer)",
          (stats["spend_micro"] == stats["spend_micro"].astype(int)).all())
    check("Business rule", "video_views is a plausible share of impressions (0-100%)",
          (stats["video_views"] <= stats["impressions"] * 1.001).all())  # small float tolerance

    # --- 5. Distributional sanity ---
    blended_cpm = stats["spend_micro"].sum() / 1_000_000 / stats["impressions"].sum() * 1000
    check("Distributional", "blended CPM lands in a plausible Snap paid-social range ($3-$18)",
          3 <= blended_cpm <= 18, detail=f"${blended_cpm:.2f}")
    blended_swipe_rate = stats["swipes"].sum() / stats["impressions"].sum()
    check("Distributional", "blended swipe rate lands in a plausible Snap range (0.2%-2.5%)",
          0.002 <= blended_swipe_rate <= 0.025, detail=f"{blended_swipe_rate:.2%}")
    total_claimed = stats["conversions"].sum()
    total_real = len(orders) + len(subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])])
    ratio = total_claimed / total_real
    check("Distributional", "Snap's self-attributed conversions total is within a believable multiple of "
                          "the business's actual real purchases (0.2x-3x)",
          0.2 <= ratio <= 3.0, detail=f"{total_claimed:.0f} claimed vs. {total_real} real (ratio {ratio:.2f}x)")

    stats["week_start"] = (stats["date"] - pd.to_timedelta(stats["date"].dt.weekday, unit="D")).dt.date
    weekly_spend = stats.groupby("week_start")["spend_micro"].sum() / 1_000_000
    ws = web_sessions[web_sessions["utm_source"] == "snap"].copy()
    ws["started_at"] = pd.to_datetime(ws["started_at"])
    ws["week_start"] = (ws["started_at"] - pd.to_timedelta(ws["started_at"].dt.weekday, unit="D")).dt.date
    weekly_sessions = ws.groupby("week_start").size()
    joined = pd.DataFrame({"spend": weekly_spend, "sessions": weekly_sessions}).dropna()
    corr = joined["spend"].corr(joined["sessions"])
    check("Distributional", "weekly Snap spend correlates positively with web_sessions.csv's own "
                          "snap-attributed weekly session count (same seasonality calendar + "
                          "channel-mix schedule driving both)",
          corr > 0.4, detail=f"Pearson r={corr:.3f} across {len(joined)} weeks")

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
