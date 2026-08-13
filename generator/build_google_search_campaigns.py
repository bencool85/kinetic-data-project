"""
Phase 7 - google_search_campaigns table (1 of 4, second of the 6
paid-media platforms). Google Ads API-shaped field names (campaign
resource).

Unlike Meta, all 5 objective campaigns are evergreen here -- see
params.py's GOOGLE_SEARCH_* docstring comment for why brand_lift (a small
always-on branded-term defense campaign, not a flighted study) doesn't
get the flighted treatment on a search platform the way it did for Meta.

Output: data/google_search_campaigns.csv
"""
import datetime
import pandas as pd

from params import START_DATE, END_DATE, GOOGLE_SEARCH_DAILY_BUDGET_MICROS

CAMPAIGN_NAMES = {
    "prospecting": "Search - Prospecting - Generic Fitness Terms",
    "retargeting": "Search - RLSA - Site Visitors & Cart Abandoners",
    "lookalike": "Search - Similar Audiences - Recent Converters",
    "conversion": "Search - Branded & High-Intent Terms",
    "brand_lift": "Search - Brand Term Defense",
}
# Google Ads' AdvertisingChannelType is always SEARCH here; bidding_strategy_type
# varies by objective -- prospecting/lookalike optimize for clicks/traffic,
# retargeting/conversion/brand_lift optimize for conversions (Target CPA / Maximize Conversions).
BIDDING_STRATEGY_BY_OBJECTIVE = {
    "prospecting": "MAXIMIZE_CLICKS", "retargeting": "TARGET_CPA", "lookalike": "MAXIMIZE_CLICKS",
    "conversion": "TARGET_CPA", "brand_lift": "MAXIMIZE_CLICKS",
}


def build_google_search_campaigns():
    rows = []
    for i, (objective, name) in enumerate(CAMPAIGN_NAMES.items(), start=1):
        rows.append({
            "campaign_id": f"179{i:015d}",
            "customer_id": None,  # filled below
            "name": name,
            "ad_objective": objective,
            "advertising_channel_type": "SEARCH",
            "bidding_strategy_type": BIDDING_STRATEGY_BY_OBJECTIVE[objective],
            "status": "ENABLED",
            "campaign_budget_micros": GOOGLE_SEARCH_DAILY_BUDGET_MICROS[objective],
            "start_date": START_DATE.isoformat(),
            "end_date": None,
            "created_at": (datetime.datetime.combine(START_DATE, datetime.time(9, 0))
                            - datetime.timedelta(days=2)).isoformat(),
        })
    df = pd.DataFrame(rows)
    from params import GOOGLE_SEARCH_CUSTOMER_ID
    df["customer_id"] = GOOGLE_SEARCH_CUSTOMER_ID
    return df


if __name__ == "__main__":
    df = build_google_search_campaigns()
    df.to_csv("../data/google_search_campaigns.csv", index=False)
    print(f"Wrote {len(df)} google_search_campaigns\n")
    print(df.to_string(index=False))
