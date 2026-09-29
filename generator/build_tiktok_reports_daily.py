"""
Phase 7 - tiktok_reports_daily table (4 of 4, completes TikTok AND Phase
7). TikTok Ads Reporting API-shaped daily stats per ad. TikTok ad units
are always video, so video_views is reported at a high share of
impressions on every row (unlike Snap, which mixes video/image/collection
creative).

Same two-spend-pool structure as every other platform's daily table:
evergreen ads split each day's total TikTok channel spend (from the
shared seasonality calendar + channel-mix schedule) by
AD_OBJECTIVE_SPEND_SHARE then across ads within objective; each brand_lift
flight spends its own lifetime budget independently across its own flight
days.

Output: data/tiktok_reports_daily.csv
"""
import copy

import numpy as np
import pandas as pd

from params import (SEED, START_DATE, END_DATE, AD_OBJECTIVE_SPEND_SHARE, AD_PAUSE_DAY_RATE,
                     TIKTOK_CPM_RANGE_BY_OBJECTIVE, TIKTOK_CTR_RANGE_BY_OBJECTIVE,
                     TIKTOK_CONVERSION_RATE_BY_OBJECTIVE, TIKTOK_AVG_CONVERSION_VALUE_RANGE,
                     TIKTOK_VIDEO_VIEW_RATE_RANGE)
from paid_media_common import load_calendar_lookups, daily_channel_spend, date_range, cap_flight_at_budget


def build_tiktok_reports_daily(seed=SEED + 80):
    rng = np.random.default_rng(seed)
    week_starts, multiplier_by_week, channel_share_by_week = load_calendar_lookups()

    campaigns = pd.read_csv("../data/tiktok_campaigns.csv")
    adgroups = pd.read_csv("../data/tiktok_adgroups.csv")
    ads = pd.read_csv("../data/tiktok_ads.csv")
    ads = ads.merge(adgroups[["adgroup_id", "campaign_id"]], on="adgroup_id")
    ads = ads.merge(campaigns[["campaign_id", "ad_objective", "start_time", "end_time"]], on="campaign_id")
    ads["start_date"] = pd.to_datetime(ads["start_time"]).dt.date
    ads["end_date"] = pd.to_datetime(ads["end_time"]).dt.date

    evergreen_ads = ads[ads["ad_objective"] != "brand_lift"]
    brand_lift_ads = ads[ads["ad_objective"] == "brand_lift"]
    evergreen_by_objective = {obj: g for obj, g in evergreen_ads.groupby("ad_objective")}

    rows = []
    for d in date_range(START_DATE, END_DATE):
        total_spend = daily_channel_spend(d, "tiktok", week_starts, multiplier_by_week, channel_share_by_week, rng)
        for objective, share in AD_OBJECTIVE_SPEND_SHARE.items():
            objective_ads = evergreen_by_objective.get(objective)
            if objective_ads is None or len(objective_ads) == 0:
                continue
            objective_spend = total_spend * share
            weights = rng.uniform(0.8, 1.2, size=len(objective_ads))
            weights = weights / weights.sum()
            for (_, ad), weight in zip(objective_ads.iterrows(), weights):
                if rng.random() < AD_PAUSE_DAY_RATE:
                    continue
                rows.append(_report_row(rng, ad, d, objective_spend * weight, objective))

    for _, ad in brand_lift_ads.iterrows():
        campaign = campaigns[campaigns["campaign_id"] == ad["campaign_id"]].iloc[0]
        flight_start, flight_end = ad["start_date"], min(ad["end_date"], END_DATE)
        n_days = (flight_end - flight_start).days + 1
        daily_target = (campaign["budget_micro"] / 1_000_000) / n_days
        flight_days = []
        for d in date_range(flight_start, flight_end):
            if rng.random() < AD_PAUSE_DAY_RATE:
                continue
            spend = daily_target * rng.lognormal(mean=0.0, sigma=0.20)
            state = copy.deepcopy(rng.bit_generator.state)
            flight_days.append((state, ad, d, spend, _report_row(rng, ad, d, spend, "brand_lift")))
        rows.extend(cap_flight_at_budget(flight_days, (campaign["budget_micro"] / 1_000_000), _report_row, "spend_micro", 1e-6))

    df = pd.DataFrame(rows).sort_values(["date", "ad_id"]).reset_index(drop=True)
    return df


def _report_row(rng, ad, d, spend, objective):
    cpm_lo, cpm_hi = TIKTOK_CPM_RANGE_BY_OBJECTIVE[objective]
    ctr_lo, ctr_hi = TIKTOK_CTR_RANGE_BY_OBJECTIVE[objective]
    vv_lo, vv_hi = TIKTOK_VIDEO_VIEW_RATE_RANGE

    cpm = rng.uniform(cpm_lo, cpm_hi)
    ctr = rng.uniform(ctr_lo, ctr_hi)
    video_view_rate = rng.uniform(vv_lo, vv_hi)

    impressions = max(1, int(round(spend / cpm * 1000)))
    clicks = max(0, int(round(impressions * ctr)))
    video_views = int(round(impressions * video_view_rate))
    spend_micro = int(round(spend * 1_000_000))

    conv_rate = TIKTOK_CONVERSION_RATE_BY_OBJECTIVE[objective] * rng.uniform(0.7, 1.3)
    conversions = round(clicks * conv_rate, 2)
    value_lo, value_hi = TIKTOK_AVG_CONVERSION_VALUE_RANGE
    conversions_value = round(conversions * rng.uniform(value_lo, value_hi), 2)

    return {
        "ad_id": ad["ad_id"], "adgroup_id": ad["adgroup_id"], "campaign_id": ad["campaign_id"],
        "date": d.isoformat(), "impressions": impressions, "clicks": clicks, "video_views": video_views,
        "spend_micro": spend_micro, "cpm_micro": int(round(spend_micro / impressions * 1000)),
        "ctr": round(clicks / impressions, 6),
        "conversions": conversions, "conversions_value": conversions_value,
    }


if __name__ == "__main__":
    df = build_tiktok_reports_daily()
    df.to_csv("../data/tiktok_reports_daily.csv", index=False)
    print(f"Wrote {len(df)} tiktok_reports_daily rows\n")
    print(f"Total spend: ${df['spend_micro'].sum() / 1_000_000:,.2f}")
    print(f"Total impressions: {df['impressions'].sum():,}")
    print(f"Total conversions: {df['conversions'].sum():,.1f}")
    print(f"Blended CPM: ${df['spend_micro'].sum()/1e6/df['impressions'].sum()*1000:.2f}")
