"""
Phase 1 - product_variants table.

Design: courses are digital, single-variant ("Standard Access"). Sized apparel
(tee, shorts, pullover) gets S/M/L/XL. The cap gets "One Size" (real-world caps
are rarely sized S-XL, unlike the other apparel) rather than the blanket
S/M/L/XL originally sketched -- a small realism refinement made while building
this table. Non-apparel merch (water bottle, resistance band set, yoga mat
bundle) gets a single default variant. No price adjustment per variant (kept
uniform -- the product's base_price already sets the price).

Output: data/product_variants.csv
"""
import pandas as pd

from params import START_DATE

SIZES = ["S", "M", "L", "XL"]

# product_id -> list of option values for its variants
VARIANT_PLAN = {
    "prod_0001": ["Standard Access"],      # Foundations: 5-Minute Mobility (course)
    "prod_0002": ["Standard Access"],      # 6-Week Strength Fundamentals (course)
    "prod_0003": ["Standard Access"],      # 8-Week HIIT Conditioning (course)
    "prod_0004": ["Standard Access"],      # 12-Week Total Body Transformation (course)
    "prod_0005": ["Standard Access"],      # Marathon Prep: 16-Week Program (course)
    "prod_0006": ["One Size"],             # Kinetic Logo Cap
    "prod_0007": ["Default"],              # Kinetic Water Bottle
    "prod_0008": SIZES,                    # Kinetic Performance Tee
    "prod_0009": SIZES,                    # Kinetic Training Shorts
    "prod_0010": SIZES,                    # Kinetic Quarter-Zip Pullover
    "prod_0011": ["Default"],              # Kinetic Resistance Band Set
    "prod_0012": ["Default"],              # Kinetic Yoga Mat + Block Bundle
}


def build_product_variants():
    products = pd.read_csv("../data/products.csv")
    prod_lookup = products.set_index("product_id")["name"].to_dict()

    rows = []
    variant_num = 0
    for product_id, options in VARIANT_PLAN.items():
        for option_value in options:
            variant_num += 1
            variant_id = f"var_{variant_num:04d}"
            # short SKU: product number + option code
            option_code = "".join(c for c in option_value.upper() if c.isalnum())[:8]
            sku = f"{product_id.replace('prod_', 'KIN-')}-{option_code}"
            rows.append({
                "variant_id": variant_id,
                "product_id": product_id,
                "sku": sku,
                "option_value": option_value,
                "price_adjustment": 0.00,
                "is_active": True,
                "created_at": START_DATE.isoformat(),
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_product_variants()
    df.to_csv("../data/product_variants.csv", index=False)
    print(f"Wrote {len(df)} product variants across {df['product_id'].nunique()} products\n")
    print(df.to_string(index=False))
