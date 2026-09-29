"""
Phase 7 - youtube_performance_daily table (3 of 3, completes YouTube).
Google Ads video-campaign metrics: video_views, video_view_rate,
average_cpv (schema_reference.md's own callout for this table), plus the
standard impressions/clicks/cost_micros/conversions fields.

Same two-spend-pool structure as meta_ad_insights_daily.py: evergreen ad
groups split each day's total YouTube channel spend (from the shared
seasonality calendar + channel-mix schedule) by AD_OBJECTIVE_SPEND_SHARE,
then across ad groups within objective; each brand_lift flight spends its
own lifetime_budget_micros independently across its own flight days.

Video economics differ from Meta's impression-driven model: spend buys
VIEWS directly (cost-per-view bidding), and impressions/clicks are then
derived FROM views (impressions = views / view_rate, clicks = impressions
x a small companion-banner click rate) rather than the other way around --
this is what real TrueView/bumper billing actually optimizes for.

Output: data/youtube_performance_daily.csv
"""
import copy

import numpy as np
import pandas as pd

from params import (SEED, START_DATE, END_DATE, AD_OBJECTIVE_SPEND_SHARE, AD_PAUSE_DAY_RATE,
                     YOUTUBE_CPV_RANGE_BY_OBJECTIVE, YOUTUBE_VIEW_RATE_RANGE_BY_OBJECTIVE,
                     YOUTUBE_CLICK_RATE_RANGE_BY_OBJECTIVE, YOUTUBE_CONVERSION_RATE_BY_OBJECTIVE,
                     YOUTUBE_AVG_CONVERSION_VALUE_RANGE)
from paid_media_common import load_calendar_lookups, daily_channel_spend, date_range, cap_flight_at_budget


def build_youtube_performance_daily(seed=SEED + 50):
    rng = np.random.default_rng(seed)
    week_starts, multiplier_by_week, channel_share_by_week = load_calendar_lookups()

    campaigns = pd.read_csv("../data/youtube_campaigns.csv")
    ad_groups = pd.read_csv("../data/youtube_ad_groups.csv")
    ad_groups = ad_groups.merge(campaigns[["campaign_id", "ad_objective", "start_date", "end_date"]],
                                 on="campaign_id")
    ad_groups["start_date"] = pd.to_datetime(ad_groups["start_date"]).dt.date
    ad_groups["end_date"] = pd.to_datetime(ad_groups["end_date"]).dt.date  # NaT for evergreen

    evergreen = ad_groups[ad_groups["ad_objective"] != "brand_lift"]
    brand_lift = ad_groups[ad_groups["ad_objective"] == "brand_lift"]
    evergreen_by_objective = {obj: g for obj, g in evergreen.groupby("ad_objective")}

    rows = []
    for d in date_range(START_DATE, END_DATE):
        total_spend = daily_channel_spend(d, "youtube", week_starts, multiplier_by_week,
                                           channel_share_by_week, rng)
        for objective, share in AD_OBJECTIVE_SPEND_SHARE.items():
            ags = evergreen_by_objective.get(objective)
            if ags is None or len(ags) == 0:
                continue
            objective_spend = total_spend * share
            weights = rng.uniform(0.8, 1.2, size=len(ags))
            weights = weights / weights.sum()
            for (_, ag), weight in zip(ags.iterrows(), weights):
                if rng.random() < AD_PAUSE_DAY_RATE:
                    continue
                rows.append(_perf_row(rng, ag, d, objective_spend * weight, objective))

    for _, ag in brand_lift.iterrows():
        campaign = campaigns[campaigns["campaign_id"] == ag["campaign_id"]].iloc[0]
        flight_start, flight_end = ag["start_date"], min(ag["end_date"], END_DATE)
        n_days = (flight_end - flight_start).days + 1
        daily_target = (campaign["lifetime_budget_micros"] / 1_000_000) / n_days
        flight_days = []
        for d in date_range(flight_start, flight_end):
            if rng.random() < AD_PAUSE_DAY_RATE:
                continue
            spend = daily_target * rng.lognormal(mean=0.0, sigma=0.20)
            state = copy.deepcopy(rng.bit_generator.state)
            flight_days.append((state, ag, d, spend, _perf_row(rng, ag, d, spend, "brand_lift")))
        rows.extend(cap_flight_at_budget(flight_days, (campaign["lifetime_budget_micros"] / 1_000_000), _perf_row, "cost_micros", 1e-6))

    df = pd.DataFrame(rows).sort_values(["date", "ad_group_id"]).reset_index(drop=True)
    return df


def _perf_row(rng, ag, d, spend, objective):
    cpv_lo, cpv_hi = YOUTUBE_CPV_RANGE_BY_OBJECTIVE[objective]
    vr_lo, vr_hi = YOUTUBE_VIEW_RATE_RANGE_BY_OBJECTIVE[objective]
    click_lo, click_hi = YOUTUBE_CLICK_RATE_RANGE_BY_OBJECTIVE[objective]

    cpv = rng.uniform(cpv_lo, cpv_hi)
    view_rate = rng.uniform(vr_lo, vr_hi)
    click_rate = rng.uniform(click_lo, click_hi)

    video_views = max(1, int(round(spend / cpv)))
    impressions = max(video_views, int(round(video_views / view_rate)))
    clicks = int(round(impressions * click_rate))

    conv_rate = YOUTUBE_CONVERSION_RATE_BY_OBJECTIVE[objective] * rng.uniform(0.7, 1.3)
    conversions = round(video_views * conv_rate, 2)
    value_lo, value_hi = YOUTUBE_AVG_CONVERSION_VALUE_RANGE
    conversions_value = round(conversions * rng.uniform(value_lo, value_hi), 2)

    cost_micros = int(round(spend * 1_000_000))

    return {
        "campaign_id": ag["campaign_id"], "ad_group_id": ag["ad_group_id"], "date": d.isoformat(),
        "impressions": impressions, "video_views": video_views,
        "video_view_rate": round(video_views / impressions, 6),
        "clicks": clicks, "cost_micros": cost_micros,
        "average_cpv_micros": int(round(cost_micros / video_views)),
        "conversions": conversions, "conversions_value": conversions_value,
    }


if __name__ == "__main__":
    df = build_youtube_performance_daily()
    df.to_csv("../data/youtube_performance_daily.csv", index=False)
    print(f"Wrote {len(df)} youtube_performance_daily rows\n")
    print(f"Total cost: ${df['cost_micros'].sum() / 1_000_000:,.2f}")
    print(f"Total video_views: {df['video_views'].sum():,}")
    print(f"Total conversions: {df['conversions'].sum():,.1f}")
    print(f"Blended CPV: ${df['cost_micros'].sum()/1e6/df['video_views'].sum():.4f}")
