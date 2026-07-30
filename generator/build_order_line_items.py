"""
Phase 3 - order_line_items table (3 of 5). One row per order -- this
project's simulated storefront only ever generates a single product per
order (the master timeline tracks one order_type + one amount per order
event, never a multi-item cart), so line-item-level granularity here means
"which exact product + variant was this" rather than "how many items."

`orders.csv` only carries an amount (subtotal), never which specific
product -- that's genuinely a line-item-level fact deferred to this table
(consistent with normal order/order_line_item normalization: catalog-level
facts live on the line item, order-level discounts/totals live on the
order). Selecting the product is a real choice this layer has to make:
- course orders: each of the 5 course price tiers maps to exactly one
  product, so there's no ambiguity.
- merch orders: the $24.99 tier maps to TWO products (Cap, Water Bottle) --
  resolved with a random pick between them.
- Apparel products (Tee/Shorts/Pullover) have 4 size variants each; picked
  with a realistic size-distribution skew (M/L most common, S/XL less so).
  Non-apparel products have exactly one variant and need no choice.

Invariant that must hold by construction: sum(line_total) per order_id
equals that order's own subtotal exactly (quantity is always 1 in this
design, so unit_price IS line_total).

Output: data/order_line_items.csv
"""
import numpy as np
import pandas as pd

from params import SEED

SIZE_WEIGHTS = {"S": 0.20, "M": 0.35, "L": 0.30, "XL": 0.15}


def build_order_line_items(seed=SEED + 11):
    rng = np.random.default_rng(seed)
    orders = pd.read_csv("../data/orders.csv")
    products = pd.read_csv("../data/products.csv")
    variants = pd.read_csv("../data/product_variants.csv")

    variants_by_product = {pid: g for pid, g in variants.groupby("product_id")}

    rows = []
    for i, order in enumerate(orders.itertuples(), start=1):
        candidates = products[(products["product_type"] == order.order_type)
                               & (products["base_price"] == order.subtotal)]
        chosen_product = candidates.sample(n=1, random_state=int(rng.integers(0, 2**31))).iloc[0]
        product_id = chosen_product["product_id"]

        pv = variants_by_product[product_id]
        if len(pv) == 1:
            variant_id = pv.iloc[0]["variant_id"]
        else:
            weights = pv["option_value"].map(SIZE_WEIGHTS).fillna(1.0 / len(pv))
            weights = weights / weights.sum()
            variant_id = pv.sample(n=1, weights=weights, random_state=int(rng.integers(0, 2**31))).iloc[0]["variant_id"]

        rows.append({
            "line_item_id": f"li_{i:06d}",
            "order_id": order.order_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": 1,
            "unit_price": order.subtotal,
            "line_total": order.subtotal,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_order_line_items()
    df.to_csv("../data/order_line_items.csv", index=False)
    print(f"Wrote {len(df)} order_line_items\n")
    print(df["product_id"].value_counts().sort_index().to_string())
