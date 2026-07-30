"""
Phase 1 - subscription_plans table: the 4 sellable plans (Basic/Plus x
monthly/annual), Stripe-shaped. Not tied to specific products -- a subscription
of either tier grants full course-catalog access (see products.py's
is_subscription_eligible note).

Output: data/subscription_plans.csv
"""
import pandas as pd

from params import BASIC_MONTHLY, BASIC_ANNUAL, PLUS_MONTHLY, PLUS_ANNUAL, START_DATE

# (plan_id, tier, billing_interval, price)
PLANS = [
    ("plan_basic_monthly", "basic", "month", BASIC_MONTHLY),
    ("plan_basic_annual", "basic", "year", BASIC_ANNUAL),
    ("plan_plus_monthly", "plus", "month", PLUS_MONTHLY),
    ("plan_plus_annual", "plus", "year", PLUS_ANNUAL),
]


def build_subscription_plans():
    rows = []
    for plan_id, tier, interval, price in PLANS:
        rows.append({
            "plan_id": plan_id,
            "tier": tier,
            "billing_interval": interval,
            "price": price,
            "currency": "usd",
            "is_active": True,
            "created_at": START_DATE.isoformat(),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_subscription_plans()
    df.to_csv("../data/subscription_plans.csv", index=False)
    print(f"Wrote {len(df)} subscription plans\n")
    print(df.to_string(index=False))
