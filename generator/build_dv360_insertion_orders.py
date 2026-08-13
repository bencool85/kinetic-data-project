"""
Phase 7 - dv360_insertion_orders table (1 of 3, fourth of the 6 paid-media
platforms). DV360 (Display & Video 360) API-shaped insertion_order
resource -- the top-level budget/pacing container, one level above
line_items.

All 5 objective IOs are evergreen (see params.py's DV360 docstring for
why -- a programmatic "reach" buy is a continuous always-on line item, not
a flighted lift study).

Output: data/dv360_insertion_orders.csv
"""
import datetime
import pandas as pd

from params import START_DATE, DV360_ADVERTISER_ID, DV360_PERFORMANCE_GOAL_BY_OBJECTIVE, DV360_DAILY_BUDGET_MICROS

IO_NAMES = {
    "prospecting": "DV360 - Prospecting - Open Web Display",
    "retargeting": "DV360 - Retargeting - Site Visitors & Cart Abandoners",
    "lookalike": "DV360 - Lookalike - Recent Converters",
    "conversion": "DV360 - Conversion - Core Programmatic Buy",
    "brand_lift": "DV360 - Awareness - Video & Connected TV Reach",
}


def build_dv360_insertion_orders():
    rows = []
    for i, (objective, name) in enumerate(IO_NAMES.items(), start=1):
        rows.append({
            "insertion_order_id": f"200{i:015d}",
            "advertiser_id": DV360_ADVERTISER_ID,
            "name": name,
            "ad_objective": objective,
            "performance_goal_type": DV360_PERFORMANCE_GOAL_BY_OBJECTIVE[objective],
            "pacing_type": "PACING_TYPE_EVEN",
            "budget_type": "INSERTION_ORDER_BUDGET_TYPE_AUTOMATIC",
            "budget_micros": DV360_DAILY_BUDGET_MICROS[objective] * 30,  # DV360 IO budgets are set at the
                                                                          # flight/monthly grain, not daily
            "status": "ENTITY_STATUS_ACTIVE",
            "start_date": START_DATE.isoformat(),
            "end_date": None,
            "created_at": (datetime.datetime.combine(START_DATE, datetime.time(9, 0))
                            - datetime.timedelta(days=2)).isoformat(),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_dv360_insertion_orders()
    df.to_csv("../data/dv360_insertion_orders.csv", index=False)
    print(f"Wrote {len(df)} dv360_insertion_orders\n")
    print(df.to_string(index=False))
