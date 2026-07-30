"""
Validation for `order_line_items` (Phase 3, table 3 of 5) -- pandas-based,
same 5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

Central cross-checks: exactly one line item per order (this simulated
storefront never generates multi-item carts); every line item's product
matches BOTH the order's order_type and its exact subtotal (price tier);
every apparel variant actually belongs to its own product; and the
per-order sum(line_total) reconciles exactly against orders.csv's own
subtotal -- the real point of this table existing at all.
"""
import pandas as pd

from params import SEED
import build_order_line_items as boli

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    items = pd.read_csv("../data/order_line_items.csv")
    orders = pd.read_csv("../data/orders.csv")
    products = pd.read_csv("../data/products.csv")
    variants = pd.read_csv("../data/product_variants.csv")

    # --- 1. Structural ---
    check("Structural", "line_item_id non-null and unique",
          items["line_item_id"].notna().all() and items["line_item_id"].is_unique)
    check("Structural", "order_id, product_id, variant_id all non-null",
          items[["order_id", "product_id", "variant_id"]].notna().all().all())
    check("Structural", "quantity is always a positive integer",
          (items["quantity"] > 0).all() and (items["quantity"] == items["quantity"].astype(int)).all())
    check("Structural", "unit_price > 0 and line_total > 0 on every row",
          (items["unit_price"] > 0).all() and (items["line_total"] > 0).all())
    check("Structural", "line_total == quantity * unit_price exactly",
          (items["line_total"].round(2) == (items["quantity"] * items["unit_price"]).round(2)).all())

    # --- 2. Referential integrity ---
    check("Referential", "every order_id exists in orders.csv, and each is referenced exactly once "
                        "(one line item per order in this design -- no multi-item carts)",
          items["order_id"].isin(orders["order_id"]).all()
          and not items["order_id"].duplicated().any()
          and set(items["order_id"]) == set(orders["order_id"]))
    check("Referential", "every product_id exists in products.csv", items["product_id"].isin(products["product_id"]).all())
    check("Referential", "every variant_id exists in product_variants.csv, and belongs to its row's own product_id",
          items.merge(variants[["variant_id", "product_id"]], on="variant_id", suffixes=("", "_variant"))
          .pipe(lambda d: (d["product_id"] == d["product_id_variant"]).all())
          and items["variant_id"].isin(variants["variant_id"]).all())

    # --- 3. Temporal ordering ---
    check("Temporal", "n/a -- order_line_items carries no dates of its own (inherits order_date via order_id)", True)

    # --- 4. Business-rule invariants ---
    joined = items.merge(orders[["order_id", "order_type", "subtotal"]], on="order_id") \
                  .merge(products[["product_id", "product_type", "base_price"]], on="product_id")
    check("Business rule", "every line item's product_type matches its order's order_type exactly",
          (joined["product_type"] == joined["order_type"]).all())
    check("Business rule", "every line item's product base_price matches its order's subtotal exactly "
                          "(the chosen product genuinely corresponds to the priced tier, not just a random product)",
          (joined["base_price"] == joined["subtotal"]).all())
    check("Business rule", "per-order sum(line_total) reconciles exactly against orders.csv's own subtotal",
          items.groupby("order_id")["line_total"].sum().round(2).equals(
              orders.set_index("order_id").loc[items.groupby("order_id")["line_total"].sum().index, "subtotal"].round(2)))

    # --- 5. Distributional sanity ---
    check("Distributional", "all 12 catalog products appear at least once (no product silently never selected)",
          items["product_id"].nunique() == len(products))
    apparel_products = products.loc[products["name"].str.contains("Tee|Shorts|Pullover"), "product_id"]
    apparel_variant_counts = items[items["product_id"].isin(apparel_products)].merge(
        variants[["variant_id", "option_value"]], on="variant_id")["option_value"].value_counts(normalize=True)
    check("Distributional", "apparel size distribution roughly matches the configured skew (M/L most common)",
          apparel_variant_counts.idxmax() in ("M", "L"))

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
