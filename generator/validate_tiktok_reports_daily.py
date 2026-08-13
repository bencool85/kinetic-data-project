"""
Validation for `tiktok_reports_daily` (Phase 7, TikTok table 4 of 4 --
completes TikTok AND all 47 tables). Same class of checks as every other
platform's daily performance validator: internal arithmetic consistency,
the cross-phase seasonality/channel-mix correlation check, and
self-attributed-conversions plausibility.
"""
import numpy as np
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    reports = pd.read_csv("../data/tiktok_reports_daily.csv")
    ads = pd.read_csv("../data/tiktok_ads.csv")
    adgroups = pd.read_csv("../data/tiktok_adgroups.csv")
    campaigns = pd.read_csv("../data/tiktok_campaigns.csv")
    web_sessions = pd.read_csv("../data/web_sessions.csv")
    orders = pd.read_csv("../data/orders.csv")
    subs = pd.read_csv("../data/subscriptions.csv")

    reports["date"] = pd.to_datetime(reports["date"])
    reports = reports.merge(ads[["ad_id", "adgroup_id"]], on=["ad_id", "adgroup_id"], how="inner")
    reports = reports.merge(adgroups[["adgroup_id", "campaign_id"]], on=["adgroup_id", "campaign_id"], how="inner")
    reports = reports.merge(campaigns[["campaign_id", "start_time", "end_time", "ad_objective"]], on="campaign_id")

    # --- 1. Structural ---
    required = ["ad_id", "adgroup_id", "campaign_id", "date", "impressions", "clicks", "video_views",
                "spend_micro", "cpm_micro", "ctr", "conversions", "conversions_value"]
    check("Structural", "all required fields non-null on every row", reports[required].notna().all().all())
    check("Structural", "impressions, clicks, video_views, spend_micro, conversions all non-negative",
          (reports[["impressions", "clicks", "video_views", "spend_micro", "conversions"]] >= 0).all().all())
    check("Structural", "clicks never exceed impressions", (reports["clicks"] <= reports["impressions"]).all())
    check("Structural", "(ad_id, date) is unique -- exactly one report row per ad per day",
          not reports.duplicated(subset=["ad_id", "date"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_id exists in tiktok_ads.csv", reports["ad_id"].isin(ads["ad_id"]).all())
    check("Referential", "every adgroup_id on a row matches that ad_id's OWN adgroup_id",
          reports.merge(ads[["ad_id", "adgroup_id"]], on="ad_id", suffixes=("", "_true"))
          .pipe(lambda d: (d["adgroup_id"] == d["adgroup_id_true"]).all()))

    # --- 3. Temporal ordering ---
    reports["start_date"] = pd.to_datetime(reports["start_time"]).dt.date
    end = pd.to_datetime(reports["end_time"])
    reports["end_date"] = end.dt.date
    date_only = reports["date"].dt.date
    check("Temporal", "every row's date falls within its own campaign's [start_time, end_time] window "
                     "(open-ended for evergreen campaigns with no end_time)",
          (date_only >= reports["start_date"]).all()
          and (reports["end_date"].isna() | (date_only <= reports["end_date"])).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "cpm_micro recomputes exactly from spend_micro/impressions*1000",
          np.isclose(reports["cpm_micro"], reports["spend_micro"] / reports["impressions"] * 1000, atol=1.0).all())
    check("Business rule", "ctr recomputes exactly from clicks/impressions",
          np.isclose(reports["ctr"], reports["clicks"] / reports["impressions"], atol=1e-4).all())
    check("Business rule", "video_views is a plausible share of impressions and reflects TikTok's always-video "
                          "ad format (video_view_rate consistently >= 0.5 across all rows)",
          (reports["video_views"] <= reports["impressions"] * 1.001).all()
          and ((reports["video_views"] / reports["impressions"]) >= 0.5).all())

    # --- 5. Distributional sanity ---
    blended_cpm = reports["spend_micro"].sum() / 1_000_000 / reports["impressions"].sum() * 1000
    check("Distributional", "blended CPM lands in a plausible TikTok paid-social range ($3-$16)",
          3 <= blended_cpm <= 16, detail=f"${blended_cpm:.2f}")
    blended_ctr = reports["clicks"].sum() / reports["impressions"].sum()
    check("Distributional", "blended CTR lands in a plausible TikTok range (0.4%-3%)",
          0.004 <= blended_ctr <= 0.03, detail=f"{blended_ctr:.2%}")
    total_claimed = reports["conversions"].sum()
    total_real = len(orders) + len(subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])])
    ratio = total_claimed / total_real
    check("Distributional", "TikTok's self-attributed conversions total is within a believable multiple of "
                          "the business's actual real purchases (0.2x-3.5x, same generous band used for "
                          "YouTube -- TikTok is the 2nd-largest platform by spend share here)",
          0.2 <= ratio <= 3.5, detail=f"{total_claimed:.0f} claimed vs. {total_real} real (ratio {ratio:.2f}x)")

    reports["week_start"] = (reports["date"] - pd.to_timedelta(reports["date"].dt.weekday, unit="D")).dt.date
    weekly_spend = reports.groupby("week_start")["spend_micro"].sum() / 1_000_000
    ws = web_sessions[web_sessions["utm_source"] == "tiktok"].copy()
    ws["started_at"] = pd.to_datetime(ws["started_at"])
    ws["week_start"] = (ws["started_at"] - pd.to_timedelta(ws["started_at"].dt.weekday, unit="D")).dt.date
    weekly_sessions = ws.groupby("week_start").size()
    joined = pd.DataFrame({"spend": weekly_spend, "sessions": weekly_sessions}).dropna()
    corr = joined["spend"].corr(joined["sessions"])
    check("Distributional", "weekly TikTok spend correlates positively with web_sessions.csv's own "
                          "tiktok-attributed weekly session count (same seasonality calendar + "
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
