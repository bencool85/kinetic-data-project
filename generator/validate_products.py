"""
Validation for the `products` table (Phase 1), first of the 47 shipped tables.

Note on tooling: the generation plan calls for loading each table into DuckDB
and validating via SQL. DuckDB isn't installable in this sandbox (no network
access to fetch new packages), so this validator reimplements the same 5-layer
approach directly in pandas -- structural, referential, temporal, business-rule,
distributional -- with identical rigor, just expressed as boolean checks over
DataFrames instead of SQL. Every later table's validator will follow this same
pattern and note the substitution once rather than repeating it.

The key "does this match the simulation" check: every price that appears in
the Phase 0 master timeline's order_events (course + merch, including the
subscriber merch discount) and the anonymous ghost population's guest
purchases must resolve to a real product of the matching type in this table.
If it doesn't, Phase 3's order_line_items would have no real product to link
an order to -- exactly the kind of impossible cross-table state this whole
project is structured to prevent.
"""
import datetime
import json
import pandas as pd

from params import COURSE_PRICE_TIERS, MERCH_PRICE_TIERS, SUBSCRIBER_MERCH_DISCOUNT, END_DATE

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    products = pd.read_csv("../data/products.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")

    # --- 1. Structural ---
    check("Structural", "product_id non-null and unique",
          products["product_id"].notna().all() and products["product_id"].is_unique)
    check("Structural", "name non-null", products["name"].notna().all())
    check("Structural", "product_type in {course, merch}",
          products["product_type"].isin(["course", "merch"]).all())
    check("Structural", "category non-null", products["category"].notna().all())
    check("Structural", "base_price > 0", (products["base_price"] > 0).all())
    check("Structural", "is_subscription_eligible is boolean",
          products["is_subscription_eligible"].isin([True, False]).all())
    check("Structural", "created_at parses as a valid date and is <= END_DATE",
          pd.to_datetime(products["created_at"]).le(pd.Timestamp(END_DATE)).all())
    check("Structural", "is_active is boolean", products["is_active"].isin([True, False]).all())

    # --- 2. Referential integrity ---
    # products has no outward foreign keys (it's the root of the catalog) --
    # nothing to check yet. Recorded for completeness / consistent layer count.
    check("Referential", "no outward FKs from products (root table, n/a by design)", True)

    # --- 3. Temporal ordering ---
    order_dates = [datetime.date.fromisoformat(o["date"])
                   for t in timeline for o in t["order_events"]]
    guest_dates = [datetime.date.fromisoformat(d)
                   for d in anon.loc[anon["is_guest_purchaser"], "guest_purchase_date"]]
    earliest_order_date = min(order_dates + guest_dates)
    created_at = pd.to_datetime(products["created_at"]).min().date()
    check("Temporal", "catalog created_at predates every simulated order date",
          created_at <= earliest_order_date,
          f"created_at={created_at}, earliest simulated order={earliest_order_date}")

    # --- 4. Business-rule invariants ---
    check("Business rule", "is_subscription_eligible is True only for course products",
          (products.loc[products["is_subscription_eligible"], "product_type"] == "course").all())
    check("Business rule", "is_subscription_eligible is False for every merch product",
          (~products.loc[products["product_type"] == "merch", "is_subscription_eligible"]).all())

    course_prices_in_sim = {round(o["amount"], 2) for t in timeline for o in t["order_events"]
                             if o["order_type"] == "course"}
    merch_prices_in_sim = {round(o["amount"], 2) for t in timeline for o in t["order_events"]
                            if o["order_type"] == "merch"}
    guest_prices_in_sim = {round(a, 2) for a in anon.loc[anon["is_guest_purchaser"], "guest_purchase_amount"]}

    course_catalog_prices = set(products.loc[products["product_type"] == "course", "base_price"].round(2))
    merch_catalog_prices = set(products.loc[products["product_type"] == "merch", "base_price"].round(2))
    # Merch bought *while actively subscribed* is discounted (SUBSCRIBER_MERCH_DISCOUNT),
    # so the allowed set of observed merch prices is the catalog price OR that
    # price discounted -- checking against raw catalog price alone would wrongly
    # fail every discounted subscriber purchase.
    merch_allowed_prices = merch_catalog_prices | {round(p * (1 - SUBSCRIBER_MERCH_DISCOUNT), 2)
                                                     for p in merch_catalog_prices}

    check("Business rule", "every simulated course order price matches a real course product's base_price",
          course_prices_in_sim <= course_catalog_prices,
          f"unmatched: {course_prices_in_sim - course_catalog_prices}")
    check("Business rule",
          "every simulated customer merch order price matches a real merch product (full or subscriber-discounted price)",
          merch_prices_in_sim <= merch_allowed_prices,
          f"unmatched: {merch_prices_in_sim - merch_allowed_prices}")
    check("Business rule", "every guest (anonymous) merch purchase price matches a real merch product at full price",
          guest_prices_in_sim <= merch_catalog_prices,
          f"unmatched: {guest_prices_in_sim - merch_catalog_prices}  (guests are never subscribers, so never discounted)")

    # --- 5. Distributional sanity ---
    check("Distributional", "12 total products: 5 course, 7 merch, as designed",
          len(products) == 12
          and (products["product_type"] == "course").sum() == 5
          and (products["product_type"] == "merch").sum() == 7)
    check("Distributional", "all 5 COURSE_PRICE_TIERS values are represented in the catalog",
          set(round(p, 2) for p in COURSE_PRICE_TIERS) <= course_catalog_prices)
    check("Distributional", "all 6 MERCH_PRICE_TIERS values are represented in the catalog",
          set(round(p, 2) for p in MERCH_PRICE_TIERS) <= merch_catalog_prices)

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
