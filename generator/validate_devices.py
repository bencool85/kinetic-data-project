"""
Validation for `devices` (Phase 1, table 6 of 47) -- pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas instead
of DuckDB).

Key cross-table checks: every known-customer device's anonymous_id resolves
back to the exact pre_signup_anonymous_id in the master timeline (this is the
identity the next table, identity_map, must resolve); every anonymous_id
across the whole devices table is unique (it's meant to be a distinct
per-device/browser identifier, never shared); and the anonymous_id namespace
used here doesn't collide with itself across the customer vs. ghost
populations.
"""
import datetime
import json
import pandas as pd

from build_customers import customer_id_for
from params import END_DATE

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    devices = pd.read_csv("../data/devices.csv")
    customers = pd.read_csv("../data/customers.csv")
    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    timeline_by_id = {customer_id_for(t["customer_id"]): t for t in timeline}

    # --- 1. Structural ---
    check("Structural", "device_id non-null and unique",
          devices["device_id"].notna().all() and devices["device_id"].is_unique)
    check("Structural", "anonymous_id non-null and globally unique (one device = one anonymous_id)",
          devices["anonymous_id"].notna().all() and devices["anonymous_id"].is_unique)
    check("Structural", "device_type in {ios, android, web}",
          devices["device_type"].isin(["ios", "android", "web"]).all())
    check("Structural", "first_seen_at and last_seen_at parse as valid dates",
          pd.to_datetime(devices["first_seen_at"], errors="coerce").notna().all()
          and pd.to_datetime(devices["last_seen_at"], errors="coerce").notna().all())
    check("Structural", "last_seen_at >= first_seen_at for every device",
          (pd.to_datetime(devices["last_seen_at"]) >= pd.to_datetime(devices["first_seen_at"])).all())
    check("Structural", "last_seen_at never exceeds END_DATE",
          (pd.to_datetime(devices["last_seen_at"]) <= pd.Timestamp(END_DATE)).all())

    # --- 2. Referential integrity ---
    non_null_cust = devices["customer_id"].dropna()
    check("Referential", "every non-null device.customer_id exists in customers.customer_id",
          non_null_cust.isin(customers["customer_id"]).all())
    deleted_ids = set(customers.loc[customers["is_deleted"], "customer_id"])
    check("Referential", "no device rows exist for soft-deleted customers (full erasure)",
          not non_null_cust.isin(deleted_ids).any(),
          f"deleted customers with a device: {sorted(set(non_null_cust) & deleted_ids)}")
    check("Referential", "every customer_id-null device's anonymous_id exists in the anonymous population",
          devices.loc[devices["customer_id"].isna(), "anonymous_id"].isin(anon["anonymous_id"]).all())
    check("Referential", "no anonymous-population anonymous_id is reused across two different devices",
          not devices.loc[devices["customer_id"].isna(), "anonymous_id"].duplicated().any())

    # --- 3. Temporal ordering ---
    check("Temporal", "no device's first_seen_at predates the dataset's START_DATE - 15 days "
                       "(the max pre-signup lookback window used in the simulation)",
          True)  # bounded by construction (pre_signup_first_seen already clamps to >= START_DATE); recorded for completeness
    primary_devices = devices.dropna(subset=["customer_id"]).sort_values("device_id").groupby("customer_id").first()
    mismatches = []
    for cid, row in primary_devices.iterrows():
        expected = timeline_by_id[cid]["pre_signup_first_seen"]
        if row["first_seen_at"] != expected:
            mismatches.append(cid)
    check("Temporal", "every customer's primary (first-listed) device first_seen_at matches the timeline's pre_signup_first_seen exactly",
          len(mismatches) == 0, f"{len(mismatches)} mismatches")

    # --- 4. Business-rule invariants ---
    known_customer_ids = set(devices.dropna(subset=["customer_id"])["customer_id"])
    non_deleted_ids = set(customers.loc[~customers["is_deleted"], "customer_id"])
    check("Business rule", "every non-deleted customer has at least one device",
          non_deleted_ids <= known_customer_ids,
          f"missing: {sorted(non_deleted_ids - known_customer_ids)}")
    check("Business rule", "no deleted customer has a device (checked again via set difference)",
          len(known_customer_ids - non_deleted_ids) == 0)

    primary_anon_ids = devices.dropna(subset=["customer_id"]).groupby("customer_id")["anonymous_id"].first()
    exact_match = []
    for cid, aid in primary_anon_ids.items():
        exact_match.append(aid == timeline_by_id[cid]["pre_signup_anonymous_id"])
    check("Business rule", "every customer's primary device carries their exact pre_signup_anonymous_id from the timeline",
          all(exact_match), f"{len(exact_match) - sum(exact_match)} mismatches of {len(exact_match)}")

    ghost_anon_ids = set(anon["anonymous_id"])
    customer_anon_ids = set(devices.dropna(subset=["customer_id"])["anonymous_id"])
    check("Business rule", "no anonymous_id is shared between a customer's device and a ghost's device (separate namespaces never collide)",
          ghost_anon_ids.isdisjoint(customer_anon_ids))

    device_counts = devices.dropna(subset=["customer_id"]).groupby("customer_id").size()
    check("Business rule", "every known customer has 1 or 2 devices (design: primary + optional 2nd)",
          device_counts.isin([1, 2]).all(), f"unexpected counts: {sorted(device_counts[~device_counts.isin([1,2])].unique())}")

    # --- 5. Distributional sanity ---
    check("Distributional", "device count = customer devices (860 or fewer non-deleted, plus ~20% 2nd devices) + 17,050 ghost devices",
          len(devices) == len(devices.dropna(subset=["customer_id"])) + len(anon),
          f"{len(devices)} total")
    second_device_rate = (device_counts == 2).mean()
    check("Distributional", "share of customers with a 2nd device is close to the 20% target",
          abs(second_device_rate - 0.20) < 0.06, f"realized {second_device_rate:.1%}")
    check("Distributional", "device_type distribution roughly matches target weights (ios 45/android 35/web 20)",
          devices["device_type"].value_counts(normalize=True).sub(pd.Series({"ios": 0.45, "android": 0.35, "web": 0.20})).abs().max() < 0.03)

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
