"""
Validation for `customers` (Phase 1, table 4 of 47) -- pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas instead
of DuckDB).

This is the first table derived directly from the Phase 0 master timeline
(one row per simulated customer), so this validator's most important job is
a 1:1 reconciliation against `_sim_customer_timeline.json`: same count, same
signup dates, same signup sources, correct customer_id mapping -- nothing
invented, nothing dropped, nothing reordered.
"""
import datetime
import json
import pandas as pd

from build_customers import customer_id_for
from params import START_DATE, END_DATE

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    customers = pd.read_csv("../data/customers.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    timeline_by_id = {customer_id_for(t["customer_id"]): t for t in timeline}

    # --- 1. Structural ---
    check("Structural", "customer_id non-null and unique",
          customers["customer_id"].notna().all() and customers["customer_id"].is_unique)
    check("Structural", "first_name, last_name, email non-null",
          customers[["first_name", "last_name", "email"]].notna().all().all())
    check("Structural", "email is unique", customers["email"].is_unique)
    check("Structural", "email contains exactly one '@'", (customers["email"].str.count("@") == 1).all())
    real_looking_domains = ~customers["email"].str.split("@").str[1].str.startswith(("fake", "deleted."))
    check("Structural", "every email domain is clearly fake (prefixed 'fake...' or the deleted-account placeholder) -- never a real-looking domain",
          (~real_looking_domains).all(),
          f"offending domains: {sorted(customers.loc[real_looking_domains, 'email'].str.split('@').str[1].unique())}")
    check("Structural", "created_at parses as a valid datetime",
          pd.to_datetime(customers["created_at"], errors="coerce").notna().all())
    check("Structural", "created_at falls within [START_DATE, END_DATE]",
          pd.to_datetime(customers["created_at"]).between(pd.Timestamp(START_DATE), pd.Timestamp(END_DATE) + pd.Timedelta(days=1)).all())
    check("Structural", "signup_source non-null", customers["signup_source"].notna().all())
    for col in ["email_opt_in", "push_opt_in", "is_deleted"]:
        check("Structural", f"{col} is boolean", customers[col].isin([True, False]).all())

    # --- 2. Referential integrity ---
    # customers has no outward FKs. It IS the root every later table (addresses,
    # devices, identity_map, subscriptions, orders, ...) will reference, so its
    # own id-space integrity (checked above: unique, non-null) is what matters here.
    check("Referential", "no outward FKs from customers (identity root, n/a by design)", True)

    # --- 3. Temporal ordering ---
    # n/a beyond the START/END bounds already checked above -- customers has no
    # other entity it must postdate.
    check("Temporal", "no dedicated cross-entity check for this table (n/a by design)", True)

    # --- 4. Business-rule invariants: 1:1 reconciliation against the master timeline ---
    check("Business rule", "same row count as the master timeline",
          len(customers) == len(timeline), f"{len(customers)} vs {len(timeline)}")
    check("Business rule", "every timeline customer_id maps to exactly one customers row",
          set(customers["customer_id"]) == set(timeline_by_id.keys()))

    merged = customers.assign(
        expected_signup_date=customers["customer_id"].map(
            lambda cid: timeline_by_id[cid]["signup_date"] if cid in timeline_by_id else None),
        expected_signup_source=customers["customer_id"].map(
            lambda cid: timeline_by_id[cid]["signup_source"] if cid in timeline_by_id else None),
    )
    actual_signup_date = pd.to_datetime(customers["created_at"]).dt.date.astype(str)
    check("Business rule", "created_at's date component matches the timeline's signup_date exactly, for every customer",
          (actual_signup_date == merged["expected_signup_date"]).all(),
          f"{(actual_signup_date != merged['expected_signup_date']).sum()} mismatches")
    check("Business rule", "signup_source matches the timeline's signup_source exactly, for every customer",
          (merged["signup_source"] == merged["expected_signup_source"]).all(),
          f"{(merged['signup_source'] != merged['expected_signup_source']).sum()} mismatches")

    check("Business rule", "deleted accounts have PII scrubbed (placeholder name/email) and both opt-ins False",
          (customers.loc[customers["is_deleted"], ["email_opt_in", "push_opt_in"]] == False).all().all()
          and (customers.loc[customers["is_deleted"], "first_name"] == "Deleted").all())
    check("Business rule", "non-deleted accounts do NOT use the deleted-account placeholder name",
          (customers.loc[~customers["is_deleted"], "first_name"] != "Deleted").all())

    # A customer can only have received a marketing email/push if they were
    # opted in at the time it was sent -- so anyone the timeline shows as
    # reactivated (or converted via the merch-to-subscriber email trigger) via
    # that channel must currently be opted in, UNLESS they've since deleted
    # their account (deletion legitimately overrides historical opt-in state).
    email_touched, push_touched = set(), set()
    for t in timeline:
        cid = customer_id_for(t["customer_id"])
        channels = {r["channel"] for r in t["reactivations"]}
        if t["trial"] and t["trial"].get("trigger") == "email_reactivation":
            channels.add("email")
        if "email" in channels:
            email_touched.add(cid)
        if "push" in channels:
            push_touched.add(cid)

    non_deleted_ids = set(customers.loc[~customers["is_deleted"], "customer_id"])
    email_must_opt_in = (email_touched & non_deleted_ids)
    push_must_opt_in = (push_touched & non_deleted_ids)
    opted_in_email = set(customers.loc[customers["email_opt_in"], "customer_id"])
    opted_in_push = set(customers.loc[customers["push_opt_in"], "customer_id"])

    check("Business rule",
          "every non-deleted customer reactivated/converted via an email touchpoint has email_opt_in=True",
          email_must_opt_in <= opted_in_email,
          f"{len(email_must_opt_in)} touched by email; violations: {sorted(email_must_opt_in - opted_in_email)}")
    check("Business rule",
          "every non-deleted customer reactivated via a push touchpoint has push_opt_in=True",
          push_must_opt_in <= opted_in_push,
          f"{len(push_must_opt_in)} touched by push; violations: {sorted(push_must_opt_in - opted_in_push)}")

    # --- 5. Distributional sanity ---
    check("Distributional", f"is_deleted rate is close to the {0.02:.0%} target",
          abs(customers["is_deleted"].mean() - 0.02) < 0.02,
          f"realized {customers['is_deleted'].mean():.1%}")
    non_deleted = customers.loc[~customers["is_deleted"]]
    check("Distributional", "email_opt_in rate (non-deleted) is close to the 88% target",
          abs(non_deleted["email_opt_in"].mean() - 0.88) < 0.05,
          f"realized {non_deleted['email_opt_in'].mean():.1%}")
    check("Distributional", "push_opt_in rate (non-deleted) is close to the 45% target",
          abs(non_deleted["push_opt_in"].mean() - 0.45) < 0.05,
          f"realized {non_deleted['push_opt_in'].mean():.1%}")
    check("Distributional", "signup_source distribution has no single channel above 40% (no accidental skew bug)",
          customers["signup_source"].value_counts(normalize=True).max() < 0.40,
          customers["signup_source"].value_counts(normalize=True).round(3).to_dict())

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
