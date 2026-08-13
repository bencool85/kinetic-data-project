"""
Phase 7 - tiktok_campaigns table (1 of 4, last of the 6 paid-media
platforms). TikTok Ads Manager API-shaped campaign resource. Real TikTok
hierarchy is Campaign > Ad Group > Ad -- structurally the same 3-level
shape as Snap (Campaign > Ad Squad > Ad), so tiktok_adgroups.py gets its
own explicit targeting-level table, same as snap_ad_squads.py.

Same 4-evergreen + 3-flighted-brand_lift structure as Meta/YouTube/Snap.
Flight budgets ($2,300-2,700 lifetime) were calibrated up front to
TikTok's own ~17.5% average channel share (the 2nd-largest of the 6
platforms after Meta) using the same proportion-of-evergreen-baseline
approach the Snap build applied, avoiding YouTube's earlier scale bug.

Output: data/tiktok_campaigns.csv
"""
import datetime
import pandas as pd

from params import (START_DATE, END_DATE, TIKTOK_ADVERTISER_ID, TIKTOK_OBJECTIVE_BY_AD_OBJECTIVE,
                     TIKTOK_DAILY_BUDGET_MICRO, TIKTOK_BRAND_LIFT_FLIGHTS)

EVERGREEN_OBJECTIVES = ["prospecting", "retargeting", "lookalike", "conversion"]
EVERGREEN_NAMES = {
    "prospecting": "TikTok - Prospecting - Broad Reach",
    "retargeting": "TikTok - Retargeting - Site Visitors & Cart Abandoners",
    "lookalike": "TikTok - Lookalike - Recent Converters",
    "conversion": "TikTok - Conversions - Core Campaign",
}


def build_tiktok_campaigns():
    rows = []
    i = 1
    for objective in EVERGREEN_OBJECTIVES:
        rows.append({
            "campaign_id": f"175828{i:013d}",
            "advertiser_id": TIKTOK_ADVERTISER_ID,
            "campaign_name": EVERGREEN_NAMES[objective],
            "ad_objective": objective,
            "objective_type": TIKTOK_OBJECTIVE_BY_AD_OBJECTIVE[objective],
            "budget_mode": "BUDGET_MODE_DAY",
            "budget_micro": TIKTOK_DAILY_BUDGET_MICRO[objective],
            "status": "CAMPAIGN_STATUS_ENABLE",
            "create_time": (datetime.datetime.combine(START_DATE, datetime.time(9, 0))
                             - datetime.timedelta(days=2)).isoformat(),
            "start_time": datetime.datetime.combine(START_DATE, datetime.time(0, 0)).isoformat(),
            "end_time": None,
        })
        i += 1

    for flight_start, flight_len, lifetime_budget in TIKTOK_BRAND_LIFT_FLIGHTS:
        flight_end = flight_start + datetime.timedelta(days=flight_len)
        status = "CAMPAIGN_STATUS_DISABLE" if flight_end <= END_DATE else "CAMPAIGN_STATUS_ENABLE"
        rows.append({
            "campaign_id": f"175828{i:013d}",
            "advertiser_id": TIKTOK_ADVERTISER_ID,
            "campaign_name": f"TikTok - Reach - Holiday Flight {flight_start.year}",
            "ad_objective": "brand_lift",
            "objective_type": TIKTOK_OBJECTIVE_BY_AD_OBJECTIVE["brand_lift"],
            "budget_mode": "BUDGET_MODE_TOTAL",
            "budget_micro": lifetime_budget,
            "status": status,
            "create_time": (datetime.datetime.combine(flight_start, datetime.time(9, 0))
                             - datetime.timedelta(days=5)).isoformat(),
            "start_time": datetime.datetime.combine(flight_start, datetime.time(0, 0)).isoformat(),
            "end_time": datetime.datetime.combine(flight_end, datetime.time(23, 59)).isoformat(),
        })
        i += 1

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_tiktok_campaigns()
    df.to_csv("../data/tiktok_campaigns.csv", index=False)
    print(f"Wrote {len(df)} tiktok_campaigns\n")
    print(df.to_string(index=False))
