"""
Validation for `identity_map` (Phase 1, table 7 of 47 -- the last Phase 1
table) -- pandas-based, same 5-layer approach (see validate_products.py's
docstring for why pandas instead of DuckDB).

Key checks: every resolution's (anonymous_id, customer_id) pair exists in
devices.csv (identity_map can't invent a link devices doesn't already show);
every non-deleted customer has exactly one "signup" resolution, using their
exact pre_signup_anonymous_id; resolved_at is never before the anonymous_id's
own first_seen_at (can't resolve an identity before the device/browser was
ever seen); and signup resolutions land exactly at the customer's created_at,
never earlier (an anonymous visitor has no customer_id link until the account
actually exists).
"""
import json
import pandas as pd

from build_customers import customer_id_for

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    idmap = pd.read_csv("../data/identity_map.csv")
    devices = pd.read_csv("../data/devices.csv")
    customers = pd.read_csv("../data/customers.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    signup_anon_id = {customer_id_for(t["customer_id"]): t["pre_signup_anonymous_id"] for t in timeline}

    # --- 1. Structural ---
    check("Structural", "resolution_id non-null and unique",
          idmap["resolution_id"].notna().all() and idmap["resolution_id"].is_unique)
    check("Structural", "anonymous_id, customer_id non-null", idmap[["anonymous_id", "customer_id"]].notna().all().all())
    check("Structural", "resolution_type in {signup, login}", idmap["resolution_type"].isin(["signup", "login"]).all())
    check("Structural", "resolved_at parses as a valid datetime", pd.to_datetime(idmap["resolved_at"], errors="coerce").notna().all())
    check("Structural", "(anonymous_id, customer_id) pairs are unique -- no duplicate resolution events",
          not idmap.duplicated(subset=["anonymous_id", "customer_id"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every identity_map.customer_id exists in customers.customer_id",
          idmap["customer_id"].isin(customers["customer_id"]).all())
    deleted_ids = set(customers.loc[customers["is_deleted"], "customer_id"])
    check("Referential", "no identity_map rows exist for soft-deleted customers",
          not idmap["customer_id"].isin(deleted_ids).any())
    known_devices = devices.dropna(subset=["customer_id"])
    known_device_pairs = set(zip(known_devices["anonymous_id"], known_devices["customer_id"]))
    idmap_pairs = set(zip(idmap["anonymous_id"], idmap["customer_id"]))
    check("Referential", "every identity_map (anonymous_id, customer_id) pair exists as a customer-linked device row",
          idmap_pairs <= known_device_pairs, f"unmatched: {sorted(idmap_pairs - known_device_pairs)[:5]}")
    check("Referential", "every customer-linked device has a matching identity_map resolution (no orphaned device)",
          known_device_pairs <= idmap_pairs, f"unmatched: {sorted(known_device_pairs - idmap_pairs)[:5]}")
    known_device_count = len(known_devices)
    check("Referential", "identity_map row count equals the number of known (customer-linked) devices",
          len(idmap) == known_device_count, f"{len(idmap)} vs {known_device_count}")

    # --- 3. Temporal ordering ---
    merged = idmap.merge(devices[["anonymous_id", "customer_id", "first_seen_at"]],
                          on=["anonymous_id", "customer_id"])
    check("Temporal", "resolved_at is never before the device's own first_seen_at",
          (pd.to_datetime(merged["resolved_at"]) >= pd.to_datetime(merged["first_seen_at"])).all())

    signup_rows = idmap[idmap["resolution_type"] == "signup"].merge(
        customers[["customer_id", "created_at"]], on="customer_id")
    check("Temporal", "every signup resolution's resolved_at matches the customer's created_at exactly",
          (signup_rows["resolved_at"] == signup_rows["created_at"]).all(),
          f"{(signup_rows['resolved_at'] != signup_rows['created_at']).sum()} mismatches")

    # --- 4. Business-rule invariants ---
    non_deleted = customers.loc[~customers["is_deleted"], "customer_id"]
    signup_counts = idmap[idmap["resolution_type"] == "signup"].groupby("customer_id").size()
    check("Business rule", "every non-deleted customer has exactly one signup resolution",
          (signup_counts.reindex(non_deleted) == 1).all(),
          f"customers missing a signup resolution: {sorted(set(non_deleted) - set(signup_counts.index))}")

    signup_rows_check = idmap[idmap["resolution_type"] == "signup"]
    exact_match = [signup_anon_id.get(row["customer_id"]) == row["anonymous_id"]
                   for _, row in signup_rows_check.iterrows()]
    check("Business rule", "every signup resolution's anonymous_id matches the timeline's exact pre_signup_anonymous_id",
          all(exact_match), f"{len(exact_match) - sum(exact_match)} mismatches of {len(exact_match)}")

    login_counts = idmap[idmap["resolution_type"] == "login"].groupby("customer_id").size()
    check("Business rule", "no customer has more than one login resolution (matches devices' 1-or-2-device design)",
          (login_counts <= 1).all())

    # --- 5. Distributional sanity ---
    check("Distributional", "849 signup resolutions (one per non-deleted customer)",
          (idmap["resolution_type"] == "signup").sum() == len(non_deleted))
    login_rate = (idmap["resolution_type"] == "login").sum() / len(non_deleted)
    check("Distributional", "login-resolution rate is close to the 2nd-device rate seen in devices.csv (~15-20%)",
          0.10 < login_rate < 0.30, f"realized {login_rate:.1%}")

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
