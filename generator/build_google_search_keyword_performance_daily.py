"""
Phase 7 - google_search_keyword_performance_daily table (4 of 4 by
schema_reference.md's listed order, but built THIRD here -- it's the
granular ground truth google_search_performance_daily.py aggregates up
from, same "build the fine-grained table first, derive the coarser one"
reasoning as meta_ad_actions_daily deriving from meta_ad_insights_daily,
just inverted here since keyword-level IS the finer grain for Search).

No separate keywords dimension table exists in schema_reference.md for
Google Search, so each ad group's keyword list (2-4 keywords, hand-curated
per ad-group theme, match-type mix) is defined once in KEYWORDS_BY_AD_GROUP
below and reused deterministically across every day this script generates.

Same seasonality-calendar x channel-mix-schedule spend driver as
paid_media_common.py provides for every platform: each day's total
google_search spend splits across the 5 (all-evergreen, see
build_google_search_campaigns.py) objectives, then across that objective's
ad groups, then across each ad group's own keywords. quality_score is
drawn once per keyword (objective-appropriate range) with small daily
jitter, since Google Ads quality scores are relatively stable week to
week, not freshly re-computed every day.

Output: data/google_search_keyword_performance_daily.csv
"""
import numpy as np
import pandas as pd

from params import (SEED, START_DATE, END_DATE, GOOGLE_SEARCH_OBJECTIVE_SPEND_SHARE, AD_PAUSE_DAY_RATE,
                     GOOGLE_SEARCH_CPC_RANGE_BY_OBJECTIVE, GOOGLE_SEARCH_CTR_RANGE_BY_OBJECTIVE,
                     GOOGLE_SEARCH_QUALITY_SCORE_RANGE_BY_OBJECTIVE, GOOGLE_SEARCH_MATCH_TYPE_WEIGHTS,
                     GOOGLE_SEARCH_CONVERSION_RATE_BY_OBJECTIVE, GOOGLE_SEARCH_AVG_CONVERSION_VALUE_RANGE)
from paid_media_common import load_calendar_lookups, daily_channel_spend, date_range

KEYWORDS_BY_AD_GROUP = {
    "Generic Fitness Terms": ["online fitness classes", "home workout app", "fitness subscription app"],
    "Competitor Comparison Terms": ["peloton alternative", "fitness app like peloton"],
    "RLSA - Website Visitors 30D": ["kinetic fitness", "online fitness classes"],
    "RLSA - Cart Abandoners": ["kinetic merch", "fitness gear checkout"],
    "Similar Audiences - Recent Converters": ["join fitness membership", "fitness app free trial"],
    "Branded Terms": ["kinetic fitness app", "kinetic login", "kinetic pricing"],
    "High-Intent Transactional Terms": ["buy fitness subscription", "sign up fitness classes"],
    "Brand Terms Defense": ["kinetic fitness app", "kinetic reviews", "kinetic vs peloton"],
}
MATCH_TYPE_CTR_MULTIPLIER = {"EXACT": 1.3, "PHRASE": 1.0, "BROAD": 0.75}


def _assign_keywords(rng, ad_groups):
    """One-time deterministic keyword roster per ad group: keyword_id,
    keyword_text, match_type, and a fixed base quality_score."""
    match_types = list(GOOGLE_SEARCH_MATCH_TYPE_WEIGHTS.keys())
    match_weights = list(GOOGLE_SEARCH_MATCH_TYPE_WEIGHTS.values())
    roster = []
    kw_i = 1
    for _, ag in ad_groups.iterrows():
        qs_lo, qs_hi = GOOGLE_SEARCH_QUALITY_SCORE_RANGE_BY_OBJECTIVE[ag["ad_objective"]]
        for text in KEYWORDS_BY_AD_GROUP[ag["name"]]:
            roster.append({
                "keyword_id": f"kw_{kw_i:06d}",
                "ad_group_id": ag["ad_group_id"],
                "campaign_id": ag["campaign_id"],
                "ad_objective": ag["ad_objective"],
                "keyword_text": text,
                "match_type": rng.choice(match_types, p=match_weights),
                "base_quality_score": int(rng.integers(qs_lo, qs_hi + 1)),
            })
            kw_i += 1
    return pd.DataFrame(roster)


def build_google_search_keyword_performance_daily(seed=SEED + 40):
    rng = np.random.default_rng(seed)
    week_starts, multiplier_by_week, channel_share_by_week = load_calendar_lookups()

    campaigns = pd.read_csv("../data/google_search_campaigns.csv")
    ad_groups = pd.read_csv("../data/google_search_ad_groups.csv")
    ad_groups = ad_groups.merge(campaigns[["campaign_id", "ad_objective"]], on="campaign_id")

    keywords = _assign_keywords(rng, ad_groups)
    by_objective = {obj: g for obj, g in keywords.groupby("ad_objective")}

    rows = []
    for d in date_range(START_DATE, END_DATE):
        total_spend = daily_channel_spend(d, "google_search", week_starts, multiplier_by_week,
                                           channel_share_by_week, rng)
        for objective, share in GOOGLE_SEARCH_OBJECTIVE_SPEND_SHARE.items():
            kws = by_objective.get(objective)
            if kws is None or len(kws) == 0:
                continue
            objective_spend = total_spend * share
            weights = rng.uniform(0.7, 1.3, size=len(kws))
            weights = weights / weights.sum()
            for (_, kw), weight in zip(kws.iterrows(), weights):
                if rng.random() < AD_PAUSE_DAY_RATE:
                    continue
                spend = objective_spend * weight
                rows.append(_keyword_row(rng, kw, d, spend))

    df = pd.DataFrame(rows).sort_values(["date", "keyword_id"]).reset_index(drop=True)
    return df


def _keyword_row(rng, kw, d, spend):
    objective = kw["ad_objective"]
    cpc_lo, cpc_hi = GOOGLE_SEARCH_CPC_RANGE_BY_OBJECTIVE[objective]
    ctr_lo, ctr_hi = GOOGLE_SEARCH_CTR_RANGE_BY_OBJECTIVE[objective]
    cpc = rng.uniform(cpc_lo, cpc_hi)
    ctr = rng.uniform(ctr_lo, ctr_hi) * MATCH_TYPE_CTR_MULTIPLIER[kw["match_type"]]

    clicks = max(0, int(round(spend / cpc)))
    impressions = max(clicks, int(round(clicks / ctr))) if clicks > 0 else int(round(rng.uniform(5, 40)))
    cost_micros = int(round(spend * 1_000_000))

    conv_rate = GOOGLE_SEARCH_CONVERSION_RATE_BY_OBJECTIVE[objective] * rng.uniform(0.7, 1.3)
    conversions = round(clicks * conv_rate, 2)
    value_lo, value_hi = GOOGLE_SEARCH_AVG_CONVERSION_VALUE_RANGE
    conversions_value = round(conversions * rng.uniform(value_lo, value_hi), 2)

    quality_score = int(np.clip(kw["base_quality_score"] + rng.integers(-1, 2), 1, 10))

    return {
        "keyword_id": kw["keyword_id"], "ad_group_id": kw["ad_group_id"], "campaign_id": kw["campaign_id"],
        "date": d.isoformat(), "keyword_text": kw["keyword_text"], "match_type": kw["match_type"],
        "quality_score": quality_score, "impressions": impressions, "clicks": clicks,
        "cost_micros": cost_micros, "average_cpc_micros": int(round(cost_micros / clicks)) if clicks > 0 else None,
        "ctr": round(clicks / impressions, 6) if impressions > 0 else 0.0,
        "conversions": conversions, "conversions_value": conversions_value,
    }


if __name__ == "__main__":
    df = build_google_search_keyword_performance_daily()
    df.to_csv("../data/google_search_keyword_performance_daily.csv", index=False)
    print(f"Wrote {len(df)} google_search_keyword_performance_daily rows\n")
    print(f"Total cost: ${df['cost_micros'].sum() / 1_000_000:,.2f}")
    print(f"Total clicks: {df['clicks'].sum():,}")
    print(f"Total conversions: {df['conversions'].sum():,.1f}")
    print(df["match_type"].value_counts())
