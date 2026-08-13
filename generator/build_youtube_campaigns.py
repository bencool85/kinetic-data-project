"""
Phase 7 - youtube_campaigns table (1 of 3, third of the 6 paid-media
platforms). Google Ads API-shaped campaign resource with
advertising_channel_type == VIDEO (a genuinely different Google Ads
product surface than Search, per schema_reference.md).

Structurally mirrors meta_campaigns.py, not google_search_campaigns.py:
4 evergreen objective campaigns + 3 flighted brand_lift campaigns timed
near BFCM -- YouTube Brand Lift is a real, common Google measurement
product run via bumper/non-skippable formats, so a flighted study is the
realistic choice here (unlike Search's always-on brand-term defense).

Output: data/youtube_campaigns.csv
"""
import datetime
import pandas as pd

from params import (START_DATE, END_DATE, YOUTUBE_CUSTOMER_ID, YOUTUBE_AD_FORMAT_BY_OBJECTIVE,
                     YOUTUBE_BIDDING_STRATEGY_BY_OBJECTIVE, YOUTUBE_DAILY_BUDGET_MICROS,
                     YOUTUBE_BRAND_LIFT_FLIGHTS)

EVERGREEN_OBJECTIVES = ["prospecting", "retargeting", "lookalike", "conversion"]
EVERGREEN_NAMES = {
    "prospecting": "YouTube - Prospecting - TrueView In-Stream",
    "retargeting": "YouTube - Video Action - Site Visitors & Cart Abandoners",
    "lookalike": "YouTube - TrueView - Similar to Recent Converters",
    "conversion": "YouTube - Video Action - Core Conversion Campaign",
}


def build_youtube_campaigns():
    rows = []
    i = 1
    for objective in EVERGREEN_OBJECTIVES:
        rows.append({
            "campaign_id": f"191{i:015d}",
            "customer_id": YOUTUBE_CUSTOMER_ID,
            "name": EVERGREEN_NAMES[objective],
            "ad_objective": objective,
            "advertising_channel_type": "VIDEO",
            "video_ad_format": YOUTUBE_AD_FORMAT_BY_OBJECTIVE[objective],
            "bidding_strategy_type": YOUTUBE_BIDDING_STRATEGY_BY_OBJECTIVE[objective],
            "status": "ENABLED",
            "campaign_budget_micros": YOUTUBE_DAILY_BUDGET_MICROS[objective],
            "lifetime_budget_micros": None,
            "start_date": START_DATE.isoformat(),
            "end_date": None,
            "created_at": (datetime.datetime.combine(START_DATE, datetime.time(9, 0))
                            - datetime.timedelta(days=2)).isoformat(),
        })
        i += 1

    for flight_start, flight_len, lifetime_budget in YOUTUBE_BRAND_LIFT_FLIGHTS:
        flight_end = flight_start + datetime.timedelta(days=flight_len)
        status = "REMOVED" if flight_end <= END_DATE else "ENABLED"  # Google Ads convention for a finished flight
        rows.append({
            "campaign_id": f"191{i:015d}",
            "customer_id": YOUTUBE_CUSTOMER_ID,
            "name": f"YouTube - Brand Lift - Holiday Awareness {flight_start.year}",
            "ad_objective": "brand_lift",
            "advertising_channel_type": "VIDEO",
            "video_ad_format": YOUTUBE_AD_FORMAT_BY_OBJECTIVE["brand_lift"],
            "bidding_strategy_type": YOUTUBE_BIDDING_STRATEGY_BY_OBJECTIVE["brand_lift"],
            "status": status,
            "campaign_budget_micros": None,
            "lifetime_budget_micros": lifetime_budget,
            "start_date": flight_start.isoformat(),
            "end_date": flight_end.isoformat(),
            "created_at": (datetime.datetime.combine(flight_start, datetime.time(9, 0))
                            - datetime.timedelta(days=5)).isoformat(),
        })
        i += 1

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_youtube_campaigns()
    df.to_csv("../data/youtube_campaigns.csv", index=False)
    print(f"Wrote {len(df)} youtube_campaigns\n")
    print(df.to_string(index=False))
