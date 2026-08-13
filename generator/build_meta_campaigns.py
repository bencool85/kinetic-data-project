"""
Phase 7 - meta_campaigns table (1 of 4, first of the 6 paid-media
platforms). Campaigns-before-everything-else build order, same reasoning
as every other phase (ads/insights/actions need real campaigns to attach
to).

Meta's real Ads API hierarchy is Campaign > Ad Set > Ad, but
schema_reference.md's Meta section only lists meta_campaigns and meta_ads
(no ad_sets table) -- a deliberate simplification, so meta_ads carries the
ad-set-level fields (targeting, optimization_goal) directly, one level
below campaign.

7 campaigns: 4 "evergreen" (always-on for nearly the whole 3-year window,
one per non-brand_lift objective: prospecting/retargeting/lookalike/
conversion) + 3 short brand_lift flights timed near BFCM each year, which
is how real brand-lift awareness studies actually run (a handful of
flighted bursts, not an always-on spend line).

Output: data/meta_campaigns.csv
"""
import datetime
import pandas as pd

from params import START_DATE, END_DATE, META_OBJECTIVE_BY_AD_OBJECTIVE, META_DAILY_BUDGET_CENTS, \
    META_BRAND_LIFT_FLIGHTS, META_ACCOUNT_ID

EVERGREEN_OBJECTIVES = ["prospecting", "retargeting", "lookalike", "conversion"]
EVERGREEN_NAMES = {
    "prospecting": "Meta - Prospecting - Broad Reach",
    "retargeting": "Meta - Retargeting - Site Visitors & Cart Abandoners",
    "lookalike": "Meta - Lookalike - Recent Converters 1%",
    "conversion": "Meta - Conversion - Core Purchase Campaign",
}


def build_meta_campaigns():
    rows = []
    i = 1

    for objective in EVERGREEN_OBJECTIVES:
        rows.append({
            "campaign_id": f"238500{i:012d}",
            "account_id": None,  # filled below
            "name": EVERGREEN_NAMES[objective],
            "ad_objective": objective,  # our internal join key, not a real Meta API field
            "objective": META_OBJECTIVE_BY_AD_OBJECTIVE[objective],
            "status": "ACTIVE",
            "daily_budget": META_DAILY_BUDGET_CENTS[objective],
            "lifetime_budget": None,
            "start_time": datetime.datetime.combine(START_DATE, datetime.time(0, 0)).isoformat(),
            "stop_time": None,
            "created_time": (datetime.datetime.combine(START_DATE, datetime.time(9, 0))
                              - datetime.timedelta(days=2)).isoformat(),
            "updated_time": datetime.datetime.combine(END_DATE, datetime.time(9, 0)).isoformat(),
        })
        i += 1

    for flight_start, flight_len, lifetime_budget in META_BRAND_LIFT_FLIGHTS:
        flight_end = flight_start + datetime.timedelta(days=flight_len)
        status = "COMPLETED" if flight_end <= END_DATE else "ACTIVE"
        rows.append({
            "campaign_id": f"238500{i:012d}",
            "account_id": None,
            "name": f"Meta - Brand Lift - Holiday Awareness {flight_start.year}",
            "ad_objective": "brand_lift",
            "objective": META_OBJECTIVE_BY_AD_OBJECTIVE["brand_lift"],
            "status": status,
            "daily_budget": None,
            "lifetime_budget": lifetime_budget,
            "start_time": datetime.datetime.combine(flight_start, datetime.time(0, 0)).isoformat(),
            "stop_time": datetime.datetime.combine(flight_end, datetime.time(23, 59)).isoformat(),
            "created_time": (datetime.datetime.combine(flight_start, datetime.time(9, 0))
                              - datetime.timedelta(days=5)).isoformat(),
            "updated_time": datetime.datetime.combine(min(flight_end, END_DATE), datetime.time(9, 0)).isoformat(),
        })
        i += 1

    df = pd.DataFrame(rows)
    df["account_id"] = META_ACCOUNT_ID
    df = df[["campaign_id", "account_id", "name", "ad_objective", "objective", "status", "daily_budget",
             "lifetime_budget", "start_time", "stop_time", "created_time", "updated_time"]]
    return df


if __name__ == "__main__":
    df = build_meta_campaigns()
    df.to_csv("../data/meta_campaigns.csv", index=False)
    print(f"Wrote {len(df)} meta_campaigns\n")
    print(df.to_string(index=False))
