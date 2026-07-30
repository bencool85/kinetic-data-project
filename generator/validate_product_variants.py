"""
Validation for `product_variants` (Phase 1, table 2 of 47) -- pandas-based,
same 5-layer approach as `validate_products.py` (see that file's docstring for
why pandas instead of DuckDB).

This is the first table with a real foreign key to another shipped table
(product_id -> products.product_id), so the referential-integrity layer does
real work here for the first time.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    variants = pd.read_csv("../data/product_variants.csv")
    products = pd.read_csv("../data/products.csv")

    # --- 1. Structural ---
    check("Structural", "variant_id non-null and unique",
          variants["variant_id"].notna().all() and variants["variant_id"].is_unique)
    check("Structural", "product_id non-null", variants["product_id"].notna().all())
    check("Structural", "sku non-null and unique",
          variants["sku"].notna().all() and variants["sku"].is_unique)
    check("Structural", "option_value non-null", variants["option_value"].notna().all())
    check("Structural", "price_adjustment is numeric", pd.api.types.is_numeric_dtype(variants["price_adjustment"]))
    check("Structural", "is_active is boolean", variants["is_active"].isin([True, False]).all())
    check("Structural", "created_at parses as a valid date", pd.to_datetime(variants["created_at"], errors="coerce").notna().all())

    # --- 2. Referential integrity ---
    check("Referential", "every variant.product_id exists in products.product_id",
          variants["product_id"].isin(products["product_id"]).all(),
          f"orphans: {sorted(set(variants['product_id']) - set(products['product_id']))}")
    check("Referential", "every product has at least one variant (no unsellable products)",
          products["product_id"].isin(variants["product_id"]).all(),
          f"products with zero variants: {sorted(set(products['product_id']) - set(variants['product_id']))}")

    # --- 3. Temporal ordering ---
    merged = variants.merge(products[["product_id", "created_at"]], on="product_id",
                             suffixes=("_variant", "_product"))
    check("Temporal", "no variant's created_at predates its own product's created_at",
          (pd.to_datetime(merged["created_at_variant"]) >= pd.to_datetime(merged["created_at_product"])).all())

    # --- 4. Business-rule invariants ---
    course_ids = set(products.loc[products["product_type"] == "course", "product_id"])
    variant_counts = variants.groupby("product_id").size()

    check("Business rule", "every course product has exactly 1 variant (digital, no sizing)",
          (variant_counts.loc[list(course_ids)] == 1).all())
    sized_apparel = {"prod_0008", "prod_0009", "prod_0010"}  # Tee, Shorts, Pullover
    check("Business rule", "sized apparel (tee/shorts/pullover) each have exactly 4 variants (S/M/L/XL)",
          (variant_counts.loc[list(sized_apparel)] == 4).all())
    for pid in sized_apparel:
        opts = set(variants.loc[variants["product_id"] == pid, "option_value"])
        check("Business rule", f"{pid} variant options are exactly S/M/L/XL", opts == {"S", "M", "L", "XL"})
    single_variant_products = set(products["product_id"]) - course_ids - sized_apparel
    check("Business rule", "cap + non-apparel merch each have exactly 1 default/one-size variant",
          (variant_counts.loc[list(single_variant_products)] == 1).all())
    check("Business rule", "price_adjustment is 0 for every variant (base_price already sets the price)",
          (variants["price_adjustment"] == 0).all())

    # --- 5. Distributional sanity ---
    check("Distributional", "21 total variants across 12 products, as designed",
          len(variants) == 21 and variants["product_id"].nunique() == 12)

    n_fail = sum(1 for _, _, ok, _ in results if not ok)
    for layer, name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {layer}: {name}" + (f"  -- {detail}" if detail else ""))
    print(f"\n{len(results) - n_fail}/{len(results)} checks passed")
    return n_fail == 0


if __name__ == "__main__":
    ok = run()
    if not ok:
        raise SystemExit(1)
