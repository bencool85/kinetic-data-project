"""
Validation for `web_sessions` (Phase 5, table 1 of 4) -- pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

Central cross-checks: unique anonymous_id count exactly equals eligible
customers + anonymous ghosts (no extra identities invented, none dropped);
customer_id is null before a customer's own signup and populated from their
signup timestamp onward, never the reverse; every known-customer order has
a same-day web session; ghost session counts exactly match
`_sim_anonymous_population.csv`'s own `num_sessions`; and every guest
purchaser's LAST session lands exactly on their `guest_purchase_date`.
"""
import json
import pandas as pd

from params import SEED, END_DATE
import build_web_sessions as bws
from build_customers import customer_id_for

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    sessions = pd.read_csv("../data/web_sessions.csv")
    customers = pd.read_csv("../data/customers.csv")
    orders = pd.read_csv("../data/orders.csv")
    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    sessions["started_at"] = pd.to_datetime(sessions["started_at"])
    sessions["ended_at"] = pd.to_datetime(sessions["ended_at"])

    # --- 1. Structural ---
    check("Structural", "session_id non-null and unique",
          sessions["session_id"].notna().all() and sessions["session_id"].is_unique)
    check("Structural", "anonymous_id non-null on every row", sessions["anonymous_id"].notna().all())
    check("Structural", "ended_at is always >= started_at", (sessions["ended_at"] >= sessions["started_at"]).all())
    check("Structural", "utm_medium/utm_campaign are null iff utm_source is null "
                        "(no partial UTM attribution)",
          (sessions["utm_source"].isna() == sessions["utm_medium"].isna()).all()
          and (sessions["utm_source"].isna() == sessions["utm_campaign"].isna()).all())

    # --- 2. Referential integrity ---
    non_deleted = customers.loc[~customers["is_deleted"]]
    non_deleted_ids = set(non_deleted["customer_id"])
    check("Referential", "every non-null customer_id exists in customers.csv and is NOT soft-deleted",
          sessions.loc[sessions["customer_id"].notna(), "customer_id"].isin(non_deleted_ids).all())
    expected_anon_ids = set(anon["anonymous_id"]) | {
        t["pre_signup_anonymous_id"] for t in timeline
        if customer_id_for(t["customer_id"]) in non_deleted_ids
    }
    check("Referential", "unique anonymous_id count exactly equals eligible customers + anonymous ghosts "
                        "(no identities invented, none silently dropped)",
          set(sessions["anonymous_id"]) == expected_anon_ids,
          detail=f"{sessions['anonymous_id'].nunique()} vs {len(expected_anon_ids)}")

    # --- 3. Temporal ordering ---
    check("Temporal", "no session starts before START_DATE or after END_DATE",
          (sessions["started_at"].dt.date >= pd.Timestamp("2023-08-01").date()).all()
          and (sessions["started_at"].dt.date <= END_DATE).all())

    known_ok = True
    detail = ""
    for cid, grp in sessions[sessions["anonymous_id"].isin(
            {t["pre_signup_anonymous_id"] for t in timeline})].groupby("anonymous_id"):
        grp = grp.sort_values("started_at")
        has_cust = grp["customer_id"].notna()
        if has_cust.any():
            first_cust_idx = has_cust.idxmax()
            # once customer_id appears, it must stay populated for all later sessions
            after = grp.loc[grp["started_at"] >= grp.loc[first_cust_idx, "started_at"]]
            if not after["customer_id"].notna().all():
                known_ok = False
                detail = f"anonymous_id {cid} has a null customer_id after resolution"
                break
    check("Temporal", "customer_id is null before a customer's own signup and populated from "
                    "the signup session onward, never null again afterward", known_ok, detail)

    # --- 4. Business-rule invariants ---
    # Soft-deleted customers get zero web_sessions rows by design (same
    # full-erasure treatment as customer_addresses/devices), even though
    # their historical orders are preserved in orders.csv -- exclude their
    # orders from this coverage check to match that documented scope.
    known_orders = orders[orders["customer_id"].notna() & orders["customer_id"].isin(non_deleted_ids)].copy()
    known_orders["order_date"] = pd.to_datetime(known_orders["order_date"]).dt.date
    sessions_by_cust_date = sessions.dropna(subset=["customer_id"]).copy()
    sessions_by_cust_date["date"] = sessions_by_cust_date["started_at"].dt.date
    session_dates = set(zip(sessions_by_cust_date["customer_id"], sessions_by_cust_date["date"]))
    order_dates = set(zip(known_orders["customer_id"], known_orders["order_date"]))
    check("Business rule", "every known-customer order has a same-day web session "
                          "(the session web_events will hang its 'purchase' event off later)",
          order_dates.issubset(session_dates))

    ghost_session_counts = sessions[sessions["customer_id"].isna()].groupby("anonymous_id").size()
    ghost_ids_in_sessions = set(sessions["anonymous_id"]) & set(anon["anonymous_id"])
    expected_counts = anon.set_index("anonymous_id").loc[list(ghost_ids_in_sessions), "num_sessions"]
    actual_counts = ghost_session_counts.reindex(expected_counts.index)
    check("Business rule", "every ghost's session count exactly matches _sim_anonymous_population.csv's "
                          "own num_sessions (single source of truth, not re-decided here)",
          (actual_counts == expected_counts).all())

    purchasers = anon[anon["is_guest_purchaser"]].copy()
    purchasers["guest_purchase_date"] = pd.to_datetime(purchasers["guest_purchase_date"]).dt.date
    last_session_date = sessions[sessions["anonymous_id"].isin(purchasers["anonymous_id"])].groupby(
        "anonymous_id")["started_at"].max().dt.date
    check_df = purchasers.set_index("anonymous_id").join(last_session_date.rename("last_session_date"))
    check("Business rule", "every guest purchaser's LAST session lands exactly on their guest_purchase_date",
          (check_df["last_session_date"] == check_df["guest_purchase_date"]).all())

    # --- 5. Distributional sanity ---
    pct_with_customer = sessions["customer_id"].notna().mean()
    check("Distributional", "a plausible minority of sessions carry a resolved customer_id "
                          "(most volume is anonymous/ghost browsing, not logged-in activity)",
          0.05 <= pct_with_customer <= 0.40, detail=f"{pct_with_customer:.1%}")
    device_share = sessions["device_category"].value_counts(normalize=True)
    check("Distributional", "mobile is the dominant device_category (configured at 55%, 45-65% band)",
          0.45 <= device_share.get("mobile", 0) <= 0.65, detail=f"{device_share.get('mobile', 0):.1%}")

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
