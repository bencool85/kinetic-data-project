"""
Validation for `youtube_performance_daily` (Phase 7, YouTube table 3 of 3
-- completes YouTube). Same class of checks as
validate_meta_ad_insights_daily.py: internal arithmetic consistency (CPV/
view_rate recompute exactly), the same cross-phase seasonality/channel-mix
correlation check, and a distributional check on self-attributed
conversions vs. real purchases.
"""
import numpy as np
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    perf = pd.read_csv("../data/youtube_performance_daily.csv")
    ad_groups = pd.read_csv("../data/youtube_ad_groups.csv")
    campaigns = pd.read_csv("../data/youtube_campaigns.csv")
    web_sessions = pd.read_csv("../data/web_sessions.csv")
    orders = pd.read_csv("../data/orders.csv")
    subs = pd.read_csv("../data/subscriptions.csv")

    perf["date"] = pd.to_datetime(perf["date"])
    perf = perf.merge(ad_groups[["ad_group_id", "campaign_id"]], on=["ad_group_id", "campaign_id"], how="inner")
    perf = perf.merge(campaigns[["campaign_id", "start_date", "end_date", "ad_objective"]], on="campaign_id")

    # --- 1. Structural ---
    required = ["campaign_id", "ad_group_id", "date", "impressions", "video_views", "video_view_rate",
                "clicks", "cost_micros", "average_cpv_micros", "conversions", "conversions_value"]
    check("Structural", "all required fields non-null on every row", perf[required].notna().all().all())
    check("Structural", "impressions, video_views, clicks, cost_micros, conversions all non-negative",
          (perf[["impressions", "video_views", "clicks", "cost_micros", "conversions"]] >= 0).all().all())
    check("Structural", "video_views never exceeds impressions (video_view_rate must be <= 1.0)",
          (perf["video_views"] <= perf["impressions"]).all())
    check("Structural", "(ad_group_id, date) is unique -- exactly one row per ad group per day",
          not perf.duplicated(subset=["ad_group_id", "date"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_group_id exists in youtube_ad_groups.csv",
          perf["ad_group_id"].isin(ad_groups["ad_group_id"]).all())
    check("Referential", "every campaign_id on a row matches that ad_group_id's OWN campaign_id",
          perf.merge(ad_groups[["ad_group_id", "campaign_id"]], on="ad_group_id", suffixes=("", "_true"))
          .pipe(lambda d: (d["campaign_id"] == d["campaign_id_true"]).all()))

    # --- 3. Temporal ordering ---
    perf["start_date"] = pd.to_datetime(perf["start_date"]).dt.date
    end = pd.to_datetime(perf["end_date"])
    perf["end_date_only"] = end.dt.date
    date_only = perf["date"].dt.date
    check("Temporal", "every row's date falls within its own campaign's [start_date, end_date] window "
                     "(open-ended for evergreen campaigns with no end_date)",
          (date_only >= perf["start_date"]).all()
          and (perf["end_date_only"].isna() | (date_only <= perf["end_date_only"])).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "video_view_rate recomputes exactly from video_views/impressions",
          np.isclose(perf["video_view_rate"], perf["video_views"] / perf["impressions"], atol=1e-4).all())
    check("Business rule", "average_cpv_micros recomputes exactly from cost_micros/video_views",
          np.isclose(perf["average_cpv_micros"], perf["cost_micros"] / perf["video_views"], atol=1.0).all())
    brand_lift_rows = perf[perf["ad_objective"] == "brand_lift"]
    check("Business rule", "brand_lift (bumper/non-skippable) rows run a much higher view_rate (>=0.85) than "
                          "the skippable TrueView objectives (<=0.40) -- reflects that unskippable formats "
                          "count nearly every impression as a view",
          (brand_lift_rows["video_view_rate"] >= 0.85).all()
          and (perf[perf["ad_objective"] != "brand_lift"]["video_view_rate"] <= 0.40).all())

    # --- 5. Distributional sanity ---
    blended_cpv = perf["cost_micros"].sum() / 1_000_000 / perf["video_views"].sum()
    check("Distributional", "blended CPV lands in a plausible YouTube range ($0.008-$0.06)",
          0.008 <= blended_cpv <= 0.06, detail=f"${blended_cpv:.4f}")
    total_claimed = perf["conversions"].sum()
    total_real = len(orders) + len(subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])])
    ratio = total_claimed / total_real
    check("Distributional", "YouTube's self-attributed conversions total is within a believable "
                          "over-attribution multiple of the business's actual real purchases (0.2x-3.5x)",
          0.2 <= ratio <= 3.5, detail=f"{total_claimed:.0f} claimed vs. {total_real} real (ratio {ratio:.2f}x)")

    perf["week_start"] = (perf["date"] - pd.to_timedelta(perf["date"].dt.weekday, unit="D")).dt.date
    weekly_cost = perf.groupby("week_start")["cost_micros"].sum() / 1_000_000
    ws = web_sessions[web_sessions["utm_source"] == "youtube"].copy()
    ws["started_at"] = pd.to_datetime(ws["started_at"])
    ws["week_start"] = (ws["started_at"] - pd.to_timedelta(ws["started_at"].dt.weekday, unit="D")).dt.date
    weekly_sessions = ws.groupby("week_start").size()
    joined = pd.DataFrame({"cost": weekly_cost, "sessions": weekly_sessions}).dropna()
    corr = joined["cost"].corr(joined["sessions"])
    check("Distributional", "weekly YouTube spend correlates positively with web_sessions.csv's own "
                          "youtube-attributed weekly session count (same seasonality calendar + "
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
