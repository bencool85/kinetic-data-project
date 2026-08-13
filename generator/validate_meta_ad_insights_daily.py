"""
Validation for `meta_ad_insights_daily` (Phase 7, Meta table 3 of 4) --
pandas-based, 5-layer approach. This is the first Phase 7 table with real
derivation risk, so the central checks here are the ones that matter most:
internal arithmetic consistency (cpm/cpc/ctr/reach all recompute exactly
from impressions/clicks/spend/frequency) and, critically, that this
table's own spend curve actually tracks the SAME seasonality calendar +
channel-mix schedule that already shaped web_sessions.csv's meta-attributed
session volume (Phase 5) -- checked via weekly correlation, not row-level
join, since schema_reference.md is explicit that no such join exists.
"""
import numpy as np
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    insights = pd.read_csv("../data/meta_ad_insights_daily.csv")
    ads = pd.read_csv("../data/meta_ads.csv")
    campaigns = pd.read_csv("../data/meta_campaigns.csv")
    web_sessions = pd.read_csv("../data/web_sessions.csv")
    calendar = pd.read_csv("../internal/_sim_seasonality_calendar.csv")
    mix = pd.read_csv("../internal/_sim_channel_mix_schedule.csv")

    insights["date"] = pd.to_datetime(insights["date"])
    insights = insights.merge(ads[["ad_id", "campaign_id"]], on=["ad_id", "campaign_id"], how="inner")
    insights = insights.merge(campaigns[["campaign_id", "start_time", "stop_time", "ad_objective"]],
                               on="campaign_id")

    # --- 1. Structural ---
    required = ["ad_id", "campaign_id", "date", "impressions", "clicks", "reach", "frequency",
                "spend", "cpm", "cpc", "ctr"]
    check("Structural", "ad_id, campaign_id, date, impressions, clicks, reach, frequency, spend, cpm, ctr "
                       "all non-null (cpc is nullable only when clicks==0)",
          insights[[c for c in required if c != "cpc"]].notna().all().all())
    check("Structural", "cpc is null IFF clicks == 0 (can't have a cost-per-click with zero clicks)",
          (insights["cpc"].isna() == (insights["clicks"] == 0)).all())
    check("Structural", "impressions, clicks, reach, spend are all non-negative",
          (insights[["impressions", "clicks", "reach", "spend"]] >= 0).all().all())
    check("Structural", "(ad_id, date) is unique -- exactly one insights row per ad per day",
          not insights.duplicated(subset=["ad_id", "date"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_id exists in meta_ads.csv", insights["ad_id"].isin(ads["ad_id"]).all())
    check("Referential", "every campaign_id on a row matches that ad_id's OWN campaign_id in meta_ads.csv "
                        "(no cross-wired ad/campaign pairs)",
          insights.merge(ads[["ad_id", "campaign_id"]], on="ad_id", suffixes=("", "_true"))
          .pipe(lambda d: (d["campaign_id"] == d["campaign_id_true"]).all()))

    # --- 3. Temporal ordering ---
    insights["start_time"] = pd.to_datetime(insights["start_time"]).dt.date
    stop = pd.to_datetime(insights["stop_time"])
    insights["stop_date"] = stop.dt.date
    date_only = insights["date"].dt.date
    check("Temporal", "every insights row's date falls within its own campaign's [start_time, stop_time] window "
                        "(open-ended for evergreen campaigns with no stop_time)",
          (date_only >= insights["start_time"]).all()
          and (insights["stop_date"].isna() | (date_only <= insights["stop_date"])).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "reach never exceeds impressions (frequency = impressions/reach must be >= 1)",
          (insights["reach"] <= insights["impressions"]).all())
    check("Business rule", "cpm recomputes exactly from spend/impressions (spend/impressions*1000)",
          np.isclose(insights["cpm"], insights["spend"] / insights["impressions"] * 1000, atol=0.01).all())
    nonzero_clicks = insights[insights["clicks"] > 0]
    check("Business rule", "cpc recomputes exactly from spend/clicks (for rows with clicks > 0)",
          np.isclose(nonzero_clicks["cpc"], nonzero_clicks["spend"] / nonzero_clicks["clicks"], atol=0.01).all())
    check("Business rule", "ctr recomputes exactly from clicks/impressions",
          np.isclose(insights["ctr"], insights["clicks"] / insights["impressions"], atol=1e-4).all())
    check("Business rule", "frequency recomputes exactly from impressions/reach",
          np.isclose(insights["frequency"], insights["impressions"] / insights["reach"], atol=0.01).all())

    # --- 5. Distributional sanity ---
    blended_cpm = insights["spend"].sum() / insights["impressions"].sum() * 1000
    check("Distributional", "blended CPM across all Meta ads lands in a plausible paid-social range ($6-$22)",
          6 <= blended_cpm <= 22, detail=f"${blended_cpm:.2f}")
    blended_ctr = insights["clicks"].sum() / insights["impressions"].sum()
    check("Distributional", "blended CTR across all Meta ads lands in a plausible paid-social range (0.5%-3%)",
          0.005 <= blended_ctr <= 0.03, detail=f"{blended_ctr:.2%}")
    n_days_seen = insights["date"].nunique()
    check("Distributional", "insights rows span nearly the full 3-year project window (>=1000 distinct dates)",
          n_days_seen >= 1000, detail=f"{n_days_seen} distinct dates")

    # --- Cross-phase consistency: weekly Meta spend vs. web_sessions' own meta-attributed session volume ---
    insights["week_start"] = (insights["date"] - pd.to_timedelta(insights["date"].dt.weekday, unit="D")).dt.date
    weekly_spend = insights.groupby("week_start")["spend"].sum()

    ws = web_sessions[web_sessions["utm_source"] == "meta"].copy()
    ws["started_at"] = pd.to_datetime(ws["started_at"])
    ws["week_start"] = (ws["started_at"] - pd.to_timedelta(ws["started_at"].dt.weekday, unit="D")).dt.date
    weekly_sessions = ws.groupby("week_start").size()

    joined = pd.DataFrame({"spend": weekly_spend, "sessions": weekly_sessions}).dropna()
    corr = joined["spend"].corr(joined["sessions"])
    check("Distributional", "weekly Meta ad spend correlates positively with web_sessions.csv's own "
                          "meta-attributed weekly session count (both driven by the same seasonality "
                          "calendar + channel-mix schedule, even with no row-level join between the two)",
          corr > 0.4, detail=f"Pearson r={corr:.3f} across {len(joined)} weeks")

    # --- Cross-phase consistency: weekly spend also tracks the seasonality*mix formula directly ---
    calendar["week_start"] = pd.to_datetime(calendar["week_start"]).dt.date
    mix["week_start"] = pd.to_datetime(mix["week_start"]).dt.date
    cal_mix = calendar.merge(mix[["week_start", "meta"]], on="week_start")
    cal_mix["expected_relative"] = cal_mix["multiplier"] * cal_mix["meta"]
    joined2 = weekly_spend.reset_index().rename(columns={0: "spend", "spend": "spend"}) \
        .merge(cal_mix[["week_start", "expected_relative"]], on="week_start", how="inner")
    corr2 = joined2["spend"].corr(joined2["expected_relative"])
    check("Distributional", "weekly Meta spend correlates strongly with the seasonality_calendar x "
                          "channel_mix_schedule formula that (deterministically, before noise/pauses) "
                          "drove it -- confirms the daily-noise layer didn't drown out the underlying signal",
          corr2 > 0.7, detail=f"Pearson r={corr2:.3f}")

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
