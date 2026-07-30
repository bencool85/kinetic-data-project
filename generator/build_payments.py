"""
Phase 3 - payments table (4 of 5). One row per Stripe-shaped Charge
*attempt* against an order -- not one row per order.

Every order in `orders.csv` represents a purchase that ultimately succeeded
(this dataset has no abandoned-cart concept), but real storefronts routinely
see a card declined and retried within the same checkout session. That's the
realistic messiness modeled here: a small share of orders get 1 (rarer: 2)
failed charge attempts immediately before the successful one -- same
order_id, same amount/currency, a fresh payment_id + failure_code each time,
timestamped a few minutes before the successful charge. Every order gets
EXACTLY one succeeded payment (by construction: that's what "this order
happened" means in this dataset).

payment_method_type/card_brand/card_last4 are assigned independently per
attempt (a customer switching payment methods mid-retry is realistic, not
modeled as sticky). card_brand/card_last4 only populate when
payment_method_type == "card".

Output: data/payments.csv
"""
import datetime
import numpy as np
import pandas as pd

from params import (
    SEED, PAYMENT_METHOD_WEIGHTS, CARD_BRAND_WEIGHTS,
    ORDER_PAYMENT_ONE_RETRY_RATE, ORDER_PAYMENT_TWO_RETRY_RATE,
    PAYMENT_FAILURE_CODE_WEIGHTS,
)

METHODS = list(PAYMENT_METHOD_WEIGHTS.keys())
METHOD_P = list(PAYMENT_METHOD_WEIGHTS.values())
BRANDS = list(CARD_BRAND_WEIGHTS.keys())
BRAND_P = list(CARD_BRAND_WEIGHTS.values())
FAILURE_CODES = list(PAYMENT_FAILURE_CODE_WEIGHTS.keys())
FAILURE_CODE_P = list(PAYMENT_FAILURE_CODE_WEIGHTS.values())


def _payment_method(rng):
    method = str(rng.choice(METHODS, p=METHOD_P))
    if method == "card":
        brand = str(rng.choice(BRANDS, p=BRAND_P))
        last4 = f"{int(rng.integers(0, 10000)):04d}"
        return method, brand, last4
    return method, None, None


def build_payments(seed=SEED + 12):
    rng = np.random.default_rng(seed)
    orders = pd.read_csv("../data/orders.csv")

    rows = []
    payment_num = 0

    for order in orders.itertuples():
        succeeded_at = datetime.datetime.fromisoformat(order.created_at)

        roll = rng.random()
        if roll < ORDER_PAYMENT_TWO_RETRY_RATE:
            n_failed = 2
        elif roll < ORDER_PAYMENT_TWO_RETRY_RATE + ORDER_PAYMENT_ONE_RETRY_RATE:
            n_failed = 1
        else:
            n_failed = 0

        # Failed attempts happen BEFORE the successful charge, a few minutes
        # apart, earliest attempt furthest back in time.
        offsets_minutes = sorted(
            (int(rng.integers(2, 21)) for _ in range(n_failed)), reverse=True
        )
        for offset in offsets_minutes:
            payment_num += 1
            method, brand, last4 = _payment_method(rng)
            attempt_at = succeeded_at - datetime.timedelta(minutes=offset)
            rows.append({
                "payment_id": f"pay_{payment_num:06d}",
                "order_id": order.order_id,
                "customer_id": order.customer_id if pd.notna(order.customer_id) else None,
                "amount": order.total_amount,
                "currency": order.currency,
                "payment_method_type": method,
                "card_brand": brand,
                "card_last4": last4,
                "status": "failed",
                "failure_code": str(rng.choice(FAILURE_CODES, p=FAILURE_CODE_P)),
                "processed_at": attempt_at.isoformat(),
                "created_at": attempt_at.isoformat(),
            })

        payment_num += 1
        method, brand, last4 = _payment_method(rng)
        rows.append({
            "payment_id": f"pay_{payment_num:06d}",
            "order_id": order.order_id,
            "customer_id": order.customer_id if pd.notna(order.customer_id) else None,
            "amount": order.total_amount,
            "currency": order.currency,
            "payment_method_type": method,
            "card_brand": brand,
            "card_last4": last4,
            "status": "succeeded",
            "failure_code": None,
            "processed_at": succeeded_at.isoformat(),
            "created_at": succeeded_at.isoformat(),
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_payments()
    df.to_csv("../data/payments.csv", index=False)
    print(f"Wrote {len(df)} payments\n")
    print(df["status"].value_counts().to_string())
    print()
    print(df["payment_method_type"].value_counts(normalize=True).round(3).to_string())
    n_orders_with_retry = df[df["status"] == "failed"]["order_id"].nunique()
    print(f"\nOrders with >=1 failed attempt before success: {n_orders_with_retry} "
          f"({n_orders_with_retry / df['order_id'].nunique():.1%})")
