"""
Phase 7 - meta_ad_insights_daily table (3 of 4). Meta Insights API-shaped
daily delivery/performance per ad. Spend is driven by the SAME seasonality
calendar + channel-mix schedule that already shaped web_sessions.csv's own
meta-attributed session volume (see paid_media_common.py) -- so this
table's spend curve and web_sessions' meta traffic curve move together,
even with no row-level join between them (schema_reference.md: no
user-level joins from ad platforms to our own data).

Two spend pools, matching meta_campaigns.py's two campaign types:
- Evergreen (prospecting/retargeting/lookalike/conversion): each day's
  total Meta channel spend is split across the 4 objectives by
  AD_OBJECTIVE_SPEND_SHARE (sums to exactly 1.0 across these 4 -- brand_lift
  is deliberately excluded from this split, it's a separate budget), then
  split again across that objective's active ads with small per-ad noise.
- Brand lift: each flight's lifetime_budget is spread evenly (with noise)
  across its own flight days only -- not part of the evergreen daily split.

A share of ad-days get NO row at all (AD_PAUSE_DAY_RATE) -- matches how a
real ad platform's reporting API returns zero rows for zero-delivery days,
not a literal zero-spend row (same convention used for guest-purchase
session gaps etc. elsewhere in this project).

Output: data/meta_ad_insights_daily.csv
"""
import datetime
import numpy as np
import pandas as pd

from params import (SEED, START_DATE, END_DATE, AD_OBJECTIVE_SPEND_SHARE, AD_PAUSE_DAY_RATE,
                     META_CPM_RANGE_BY_OBJECTIVE, META_CTR_RANGE_BY_OBJECTIVE, META_FREQUENCY_RANGE)
from paid_media_common import load_calendar_lookups, daily_channel_spend, date_range


def build_meta_ad_insights_daily(seed=SEED + 30):
    rng = np.random.default_rng(seed)
    week_starts, multiplier_by_week, channel_share_by_week = load_calendar_lookups()

    campaigns = pd.read_csv("../data/meta_campaigns.csv")
    ads = pd.read_csv("../data/meta_ads.csv")
    ads = ads.merge(campaigns[["campaign_id", "ad_objective", "start_time", "stop_time"]], on="campaign_id")
    ads["start_date"] = pd.to_datetime(ads["start_time"]).dt.date
    ads["stop_date"] = pd.to_datetime(ads["stop_time"]).dt.date  # NaT for evergreen (no stop_time)

    evergreen_ads = ads[ads["ad_objective"] != "brand_lift"]
    brand_lift_ads = ads[ads["ad_objective"] == "brand_lift"]
    evergreen_by_objective = {obj: g for obj, g in evergreen_ads.groupby("ad_objective")}

    rows = []

    # --- Evergreen ads: full [START_DATE, END_DATE] window ---
    for d in date_range(START_DATE, END_DATE):
        total_meta_spend = daily_channel_spend(d, "meta", week_starts, multiplier_by_week, channel_share_by_week, rng)
        for objective, share in AD_OBJECTIVE_SPEND_SHARE.items():
            objective_ads = evergreen_by_objective.get(objective)
            if objective_ads is None or len(objective_ads) == 0:
                continue
            objective_spend = total_meta_spend * share
            weights = rng.uniform(0.8, 1.2, size=len(objective_ads))
            weights = weights / weights.sum()
            for (_, ad), weight in zip(objective_ads.iterrows(), weights):
                if rng.random() < AD_PAUSE_DAY_RATE:
                    continue
                spend = objective_spend * weight
                rows.append(_insight_row(rng, ad, d, spend, objective))

    # --- Brand lift ads: only within their own flight window ---
    for _, ad in brand_lift_ads.iterrows():
        campaign = campaigns[campaigns["campaign_id"] == ad["campaign_id"]].iloc[0]
        flight_start, flight_end = ad["start_date"], min(ad["stop_date"], END_DATE)
        n_days = (flight_end - flight_start).days + 1
        # lifetime_budget is stored in cents (Meta API convention, same as
        # daily_budget) -- convert to dollars before spreading across days.
        daily_target = (campaign["lifetime_budget"] / 100) / n_days
        for d in date_range(flight_start, flight_end):
            if rng.random() < AD_PAUSE_DAY_RATE:
                continue
            spend = daily_target * rng.lognormal(mean=0.0, sigma=0.20)
            rows.append(_insight_row(rng, ad, d, spend, "brand_lift"))

    df = pd.DataFrame(rows).sort_values(["date", "ad_id"]).reset_index(drop=True)
    return df


def _insight_row(rng, ad, d, spend, objective):
    cpm_lo, cpm_hi = META_CPM_RANGE_BY_OBJECTIVE[objective]
    ctr_lo, ctr_hi = META_CTR_RANGE_BY_OBJECTIVE[objective]
    freq_lo, freq_hi = META_FREQUENCY_RANGE
    cpm = rng.uniform(cpm_lo, cpm_hi)
    ctr = rng.uniform(ctr_lo, ctr_hi)
    frequency = round(rng.uniform(freq_lo, freq_hi), 2)

    impressions = max(1, int(round(spend / cpm * 1000)))
    clicks = max(0, int(round(impressions * ctr)))
    reach = max(1, int(round(impressions / frequency)))
    reach = min(reach, impressions)  # reach can never exceed impressions

    return {
        "ad_id": ad["ad_id"],
        "campaign_id": ad["campaign_id"],
        "date": d.isoformat(),
        "impressions": impressions,
        "clicks": clicks,
        "reach": reach,
        "frequency": round(impressions / reach, 4),
        "spend": round(spend, 2),
        "cpm": round(spend / impressions * 1000, 4),
        "cpc": round(spend / clicks, 4) if clicks > 0 else None,
        "ctr": round(clicks / impressions, 6),
    }


if __name__ == "__main__":
    df = build_meta_ad_insights_daily()
    df.to_csv("../data/meta_ad_insights_daily.csv", index=False)
    print(f"Wrote {len(df)} meta_ad_insights_daily rows\n")
    print(f"Total spend: ${df['spend'].sum():,.2f}")
    print(f"Total impressions: {df['impressions'].sum():,}")
    print(f"Total clicks: {df['clicks'].sum():,}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(df.groupby(df["ad_id"]).size().describe())
