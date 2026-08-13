"""
Phase 7 - snap_campaigns table (1 of 4, fifth of the 6 paid-media
platforms). Snap Ads API-shaped campaign resource. Real Snap hierarchy is
Campaign > Ad Squad > Ad, so (unlike Meta) Snap gets its own explicit
ad-squad-level targeting table (snap_ad_squads.py) -- this table just
holds the campaign-level objective/budget/status, one level up.

Same 4-evergreen + 3-flighted-brand_lift structure as Meta/YouTube, with
flight budgets calibrated (see params.py's SNAP_BRAND_LIFT_FLIGHTS
comment) to the same proportion-of-evergreen-baseline ratio Meta's flights
land at -- avoiding the scale bug caught during YouTube's build.

Output: data/snap_campaigns.csv
"""
import datetime
import pandas as pd

from params import (START_DATE, END_DATE, SNAP_AD_ACCOUNT_ID, SNAP_OBJECTIVE_BY_AD_OBJECTIVE,
                     SNAP_DAILY_BUDGET_MICRO, SNAP_BRAND_LIFT_FLIGHTS)

EVERGREEN_OBJECTIVES = ["prospecting", "retargeting", "lookalike", "conversion"]
EVERGREEN_NAMES = {
    "prospecting": "Snap - Prospecting - Broad Reach",
    "retargeting": "Snap - Retargeting - Site Visitors & Cart Abandoners",
    "lookalike": "Snap - Lookalike - Recent Converters",
    "conversion": "Snap - Web Conversions - Core Campaign",
}


def build_snap_campaigns():
    rows = []
    i = 1
    for objective in EVERGREEN_OBJECTIVES:
        rows.append({
            "campaign_id": f"00000000-0000-4000-b000-{i:012d}",
            "ad_account_id": SNAP_AD_ACCOUNT_ID,
            "name": EVERGREEN_NAMES[objective],
            "ad_objective": objective,
            "objective": SNAP_OBJECTIVE_BY_AD_OBJECTIVE[objective],
            "status": "ACTIVE",
            "daily_budget_micro": SNAP_DAILY_BUDGET_MICRO[objective],
            "lifetime_budget_micro": None,
            "start_time": datetime.datetime.combine(START_DATE, datetime.time(0, 0)).isoformat(),
            "end_time": None,
            "created_at": (datetime.datetime.combine(START_DATE, datetime.time(9, 0))
                            - datetime.timedelta(days=2)).isoformat(),
            "updated_at": datetime.datetime.combine(END_DATE, datetime.time(9, 0)).isoformat(),
        })
        i += 1

    for flight_start, flight_len, lifetime_budget in SNAP_BRAND_LIFT_FLIGHTS:
        flight_end = flight_start + datetime.timedelta(days=flight_len)
        status = "COMPLETED" if flight_end <= END_DATE else "ACTIVE"
        rows.append({
            "campaign_id": f"00000000-0000-4000-b000-{i:012d}",
            "ad_account_id": SNAP_AD_ACCOUNT_ID,
            "name": f"Snap - Awareness - Holiday Flight {flight_start.year}",
            "ad_objective": "brand_lift",
            "objective": SNAP_OBJECTIVE_BY_AD_OBJECTIVE["brand_lift"],
            "status": status,
            "daily_budget_micro": None,
            "lifetime_budget_micro": lifetime_budget,
            "start_time": datetime.datetime.combine(flight_start, datetime.time(0, 0)).isoformat(),
            "end_time": datetime.datetime.combine(flight_end, datetime.time(23, 59)).isoformat(),
            "created_at": (datetime.datetime.combine(flight_start, datetime.time(9, 0))
                            - datetime.timedelta(days=5)).isoformat(),
            "updated_at": datetime.datetime.combine(min(flight_end, END_DATE), datetime.time(9, 0)).isoformat(),
        })
        i += 1

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_snap_campaigns()
    df.to_csv("../data/snap_campaigns.csv", index=False)
    print(f"Wrote {len(df)} snap_campaigns\n")
    print(df.to_string(index=False))
