"""
Validation for `customer_addresses` (Phase 1, table 5 of 47) -- pandas-based,
same 5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).
"""
import json
import pandas as pd

from build_customers import customer_id_for

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    addresses = pd.read_csv("../data/customer_addresses.csv", dtype={"zip_code": str})
    customers = pd.read_csv("../data/customers.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    # --- 1. Structural ---
    check("Structural", "address_id non-null and unique",
          addresses["address_id"].notna().all() and addresses["address_id"].is_unique)
    check("Structural", "customer_id non-null", addresses["customer_id"].notna().all())
    check("Structural", "address_type in {billing, shipping}",
          addresses["address_type"].isin(["billing", "shipping"]).all())
    check("Structural", "street_address non-null", addresses["street_address"].notna().all())
    check("Structural", "street_address is obviously fake (contains the literal word 'Fake')",
          addresses["street_address"].str.contains(r"\bFake\b").all())
    check("Structural", "city, state, zip_code, country non-null",
          addresses[["city", "state", "zip_code", "country"]].notna().all().all())
    check("Structural", "state is a 2-letter code", (addresses["state"].str.len() == 2).all())
    check("Structural", "zip_code is a 5-digit string", addresses["zip_code"].str.match(r"^\d{5}$").all())
    check("Structural", "country is 'US'", (addresses["country"] == "US").all())
    check("Structural", "created_at parses as a valid date", pd.to_datetime(addresses["created_at"], errors="coerce").notna().all())
    check("Structural", "(customer_id, address_type) is unique -- at most one billing + one shipping row per customer",
          not addresses.duplicated(subset=["customer_id", "address_type"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every address.customer_id exists in customers.customer_id",
          addresses["customer_id"].isin(customers["customer_id"]).all())
    deleted_ids = set(customers.loc[customers["is_deleted"], "customer_id"])
    check("Referential", "no address rows exist for soft-deleted customers (full erasure)",
          not addresses["customer_id"].isin(deleted_ids).any(),
          f"deleted customers with an address: {sorted(set(addresses['customer_id']) & deleted_ids)}")

    # --- 3. Temporal ordering ---
    cust_created = customers.set_index("customer_id")["created_at"]
    merged = addresses.merge(cust_created.rename("customer_created_at"), left_on="customer_id", right_index=True)
    check("Temporal", "no address created_at predates its own customer's created_at",
          (pd.to_datetime(merged["created_at"]) >= pd.to_datetime(merged["customer_created_at"]).dt.normalize()).all())

    timeline_by_id = {customer_id_for(t["customer_id"]): t for t in timeline}
    ship_rows = addresses[addresses["address_type"] == "shipping"]
    ship_ok = []
    for _, row in ship_rows.iterrows():
        t = timeline_by_id[row["customer_id"]]
        first_merch_date = min(o["date"] for o in t["order_events"] if o["order_type"] == "merch")
        ship_ok.append(row["created_at"] == first_merch_date)
    check("Temporal", "every shipping address's created_at exactly matches its customer's first merch order date",
          all(ship_ok), f"{len(ship_ok) - sum(ship_ok)} mismatches of {len(ship_ok)}")

    # --- 4. Business-rule invariants ---
    non_deleted = customers.loc[~customers["is_deleted"]]
    billing_cust_ids = set(addresses.loc[addresses["address_type"] == "billing", "customer_id"])
    expected_billing_ids = set()
    for _, c in non_deleted.iterrows():
        t = timeline_by_id[c["customer_id"]]
        if t["account_type"] == "subscriber" or len(t["order_events"]) > 0:
            expected_billing_ids.add(c["customer_id"])
    check("Business rule", "exactly the customers who needed billing (subscriber-path OR ever ordered) have a billing address",
          billing_cust_ids == expected_billing_ids,
          f"missing: {expected_billing_ids - billing_cust_ids}, extra: {billing_cust_ids - expected_billing_ids}")

    shipping_cust_ids = set(addresses.loc[addresses["address_type"] == "shipping", "customer_id"])
    expected_shipping_ids = {c for c in non_deleted["customer_id"]
                              if any(o["order_type"] == "merch" for o in timeline_by_id[c]["order_events"])}
    check("Business rule", "exactly the customers with >=1 merch order have a shipping address",
          shipping_cust_ids == expected_shipping_ids,
          f"missing: {expected_shipping_ids - shipping_cust_ids}, extra: {shipping_cust_ids - expected_shipping_ids}")

    check("Business rule", "every customer with a shipping address also has a billing address (can't ship with no payment method on file)",
          shipping_cust_ids <= billing_cust_ids)

    # --- 5. Distributional sanity ---
    same_as_billing = 0
    compared = 0
    for cid in shipping_cust_ids & billing_cust_ids:
        b = addresses[(addresses.customer_id == cid) & (addresses.address_type == "billing")].iloc[0]
        s = addresses[(addresses.customer_id == cid) & (addresses.address_type == "shipping")].iloc[0]
        compared += 1
        if b["street_address"] == s["street_address"]:
            same_as_billing += 1
    same_rate = same_as_billing / compared if compared else 0
    check("Distributional", "share of shipping addresses matching billing is close to the 70% target",
          abs(same_rate - 0.70) < 0.08, f"realized {same_rate:.1%} ({same_as_billing}/{compared})")
    unit_rate = addresses["unit"].notna().mean()
    check("Distributional", "share of addresses with a unit/apt/suite is close to the 25% target",
          abs(unit_rate - 0.25) < 0.06, f"realized {unit_rate:.1%}")
    check("Distributional", "at least 15 distinct cities represented (no accidental collapse to 1-2 cities)",
          addresses["city"].nunique() >= 15, f"{addresses['city'].nunique()} distinct cities")

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
