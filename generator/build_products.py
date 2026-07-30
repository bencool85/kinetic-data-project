"""
Phase 1 - products table: the course + merch catalog.

Deliberately minimal (~12 items): one flagship product per price tier already
baked into the Phase 0 simulation (COURSE_PRICE_TIERS / MERCH_PRICE_TIERS),
plus one extra low-tier merch item for variety. Every price that appears in
the simulated order_events must resolve to a real product here, so Phase 3's
order_line_items has something real to link each order to.

Output: data/products.csv
"""
import pandas as pd

from params import START_DATE

# (product_id, name, product_type, category, base_price, is_subscription_eligible)
# is_subscription_eligible: True for courses -- an active subscription includes
# full course-catalog access, which is exactly why the simulation never places
# a course order during an active subscription window. Merch is physical goods,
# never included in a subscription, always purchased separately (at a discount
# if the customer happens to be subscribed at the time).
PRODUCTS = [
    ("prod_0001", "Foundations: 5-Minute Mobility", "course", "mobility", 9.99, True),
    ("prod_0002", "6-Week Strength Fundamentals", "course", "strength", 79.00, True),
    ("prod_0003", "8-Week HIIT Conditioning", "course", "conditioning", 99.00, True),
    ("prod_0004", "12-Week Total Body Transformation", "course", "transformation", 129.00, True),
    ("prod_0005", "Marathon Prep: 16-Week Program", "course", "endurance", 149.00, True),
    ("prod_0006", "Kinetic Logo Cap", "merch", "apparel", 24.99, False),
    ("prod_0007", "Kinetic Water Bottle", "merch", "accessories", 24.99, False),
    ("prod_0008", "Kinetic Performance Tee", "merch", "apparel", 34.99, False),
    ("prod_0009", "Kinetic Training Shorts", "merch", "apparel", 49.99, False),
    ("prod_0010", "Kinetic Quarter-Zip Pullover", "merch", "apparel", 64.99, False),
    ("prod_0011", "Kinetic Resistance Band Set", "merch", "equipment", 89.99, False),
    ("prod_0012", "Kinetic Yoga Mat + Block Bundle", "merch", "equipment", 120.00, False),
]


def build_products():
    rows = []
    for product_id, name, ptype, category, price, sub_eligible in PRODUCTS:
        rows.append({
            "product_id": product_id,
            "name": name,
            "product_type": ptype,
            "category": category,
            "base_price": price,
            "is_subscription_eligible": sub_eligible,
            "created_at": START_DATE.isoformat(),
            "is_active": True,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_products()
    df.to_csv("../data/products.csv", index=False)
    print(f"Wrote {len(df)} products to data/products.csv\n")
    print(df[["product_id", "name", "product_type", "category", "base_price"]].to_string(index=False))
