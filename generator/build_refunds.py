"""
Phase 3 - refunds table (5 of 5, completes Phase 3). One row per Stripe-shaped
Refund object, issued against the single succeeded payment for a small share
of orders.

Every refund is tied to `payments.csv`'s succeeded payment for that order
(never a failed attempt -- you can't refund a charge that never went
through), reusing that payment_id directly rather than re-deriving it.
Most refunds are full (the order's own total_amount); a minority are partial
-- a discretionary adjustment (shipping credit, partial goodwill), since
every order here is a single line item, not a partial-quantity return.

An order is only eligible for a refund if `order_date + minimum refund delay`
still falls on or before END_DATE -- a refund can't be recorded after the
dataset's own observation window closes. In practice this only excludes the
handful of orders placed on END_DATE itself.

Output: data/refunds.csv
"""
import datetime
import numpy as np
import pandas as pd

from params import (
    SEED, END_DATE, ORDER_REFUND_RATE, PARTIAL_REFUND_SHARE,
    PARTIAL_REFUND_FRACTION_RANGE, REFUND_REASON_WEIGHTS, REFUND_DELAY_DAYS_RANGE,
)

REASONS = list(REFUND_REASON_WEIGHTS.keys())
REASON_P = list(REFUND_REASON_WEIGHTS.values())


def build_refunds(seed=SEED + 13):
    rng = np.random.default_rng(seed)
    orders = pd.read_csv("../data/orders.csv")
    payments = pd.read_csv("../data/payments.csv")

    succeeded_payment_by_order = (
        payments[payments["status"] == "succeeded"]
        .set_index("order_id")["payment_id"]
    )

    rows = []
    refund_num = 0

    for order in orders.itertuples():
        order_date = datetime.date.fromisoformat(order.order_date)
        min_delay, max_delay = REFUND_DELAY_DAYS_RANGE
        if order_date + datetime.timedelta(days=min_delay) > END_DATE:
            continue  # not enough runway left in the dataset window for a refund to land

        if rng.random() >= ORDER_REFUND_RATE:
            continue

        # Clip the delay so the refund never lands after END_DATE.
        latest_possible_delay = min(max_delay, (END_DATE - order_date).days)
        delay_days = int(rng.integers(min_delay, latest_possible_delay + 1))
        refunded_at = order_date + datetime.timedelta(days=delay_days)

        is_partial = rng.random() < PARTIAL_REFUND_SHARE
        if is_partial:
            frac = rng.uniform(*PARTIAL_REFUND_FRACTION_RANGE)
            amount = round(order.total_amount * frac, 2)
        else:
            amount = order.total_amount

        refund_num += 1
        # Refunds fire at midday, distinct from orders' own created_at time-of-day.
        refunded_at_dt = datetime.datetime.combine(refunded_at, datetime.time(12, 0, 0))
        rows.append({
            "refund_id": f"ref_{refund_num:06d}",
            "order_id": order.order_id,
            "payment_id": succeeded_payment_by_order[order.order_id],
            "customer_id": order.customer_id if pd.notna(order.customer_id) else None,
            "amount": amount,
            "currency": order.currency,
            "is_partial": is_partial,
            "reason": str(rng.choice(REASONS, p=REASON_P)),
            "status": "succeeded",
            "refunded_at": refunded_at_dt.isoformat(),
            "created_at": refunded_at_dt.isoformat(),
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_refunds()
    df.to_csv("../data/refunds.csv", index=False)
    orders = pd.read_csv("../data/orders.csv")
    print(f"Wrote {len(df)} refunds ({len(df) / len(orders):.1%} of all orders)\n")
    print(df["is_partial"].value_counts().to_string())
    print()
    print(df["reason"].value_counts(normalize=True).round(3).to_string())
    print(f"\nTotal refunded: ${df['amount'].sum():,.2f}")
