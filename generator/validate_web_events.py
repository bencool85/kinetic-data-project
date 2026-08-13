"""
Validation for `web_events` (Phase 5, table 2 of 4) -- pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

Central cross-checks: every order belonging to a NON-deleted customer (or
any guest order) gets exactly one `purchase` event -- deleted customers'
orders are excluded from this expectation since they have zero web_sessions
rows by design, same full-erasure scope as web_sessions.csv itself;
every purchase event's product_id matches order_line_items.csv's own
product for that order exactly; every event's occurred_at falls within its
own session's [started_at, ended_at] window; and event_type-specific fields
(product_id/order_id/search_query) are populated only for the event types
that should carry them.
"""
import pandas as pd

from params import SEED
import build_web_events as bwe

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    events = pd.read_csv("../data/web_events.csv")
    sessions = pd.read_csv("../data/web_sessions.csv")
    orders = pd.read_csv("../data/orders.csv")
    line_items = pd.read_csv("../data/order_line_items.csv")
    customers = pd.read_csv("../data/customers.csv")

    events["occurred_at"] = pd.to_datetime(events["occurred_at"])
    sessions["started_at"] = pd.to_datetime(sessions["started_at"])
    sessions["ended_at"] = pd.to_datetime(sessions["ended_at"])

    # --- 1. Structural ---
    check("Structural", "event_id non-null and unique",
          events["event_id"].notna().all() and events["event_id"].is_unique)
    check("Structural", "session_id, anonymous_id, event_type, occurred_at all non-null",
          events[["session_id", "anonymous_id", "event_type", "occurred_at"]].notna().all().all())
    valid_types = {"page_view", "product_view", "add_to_cart", "begin_checkout", "purchase", "search"}
    check("Structural", "event_type is always one of the 6 schema-defined values",
          events["event_type"].isin(valid_types).all())
    check("Structural", "product_id is populated iff event_type is product_view/add_to_cart/"
                        "begin_checkout/purchase (never for page_view/search)",
          (events.loc[events["event_type"].isin(["product_view", "add_to_cart", "begin_checkout", "purchase"]),
                      "product_id"].notna().all())
          and (events.loc[events["event_type"].isin(["page_view", "search"]), "product_id"].isna().all()))
    check("Structural", "order_id is populated iff event_type == 'purchase'",
          (events.loc[events["event_type"] == "purchase", "order_id"].notna().all())
          and (events.loc[events["event_type"] != "purchase", "order_id"].isna().all()))
    check("Structural", "search_query is populated iff event_type == 'search'",
          (events.loc[events["event_type"] == "search", "search_query"].notna().all())
          and (events.loc[events["event_type"] != "search", "search_query"].isna().all()))

    # --- 2. Referential integrity ---
    check("Referential", "every session_id exists in web_sessions.csv", events["session_id"].isin(sessions["session_id"]).all())
    check("Referential", "every non-null order_id exists in orders.csv",
          events.loc[events["order_id"].notna(), "order_id"].isin(orders["order_id"]).all())
    purchase_events = events[events["event_type"] == "purchase"]
    check("Referential", "at most one purchase event per order (no double-counted purchases)",
          not purchase_events["order_id"].duplicated().any())

    # --- 3. Temporal ordering ---
    joined = events.merge(sessions[["session_id", "started_at", "ended_at"]], on="session_id")
    check("Temporal", "every event's occurred_at falls within its own session's [started_at, ended_at] window",
          ((joined["occurred_at"] >= joined["started_at"]) & (joined["occurred_at"] <= joined["ended_at"])).all())

    # --- 4. Business-rule invariants ---
    non_deleted_ids = set(customers.loc[~customers["is_deleted"], "customer_id"])
    expected_purchase_orders = set(orders.loc[
        orders["customer_id"].isna() | orders["customer_id"].isin(non_deleted_ids), "order_id"])
    actual_purchase_orders = set(purchase_events["order_id"])
    check("Business rule", "every order belonging to a non-deleted customer (or any guest order) has "
                          "exactly one purchase event",
          expected_purchase_orders == actual_purchase_orders)

    purchase_check = purchase_events.merge(
        line_items[["order_id", "product_id"]], on="order_id", suffixes=("", "_true"))
    check("Business rule", "every purchase event's product_id exactly matches order_line_items.csv's "
                          "own product for that order (the real thing they bought, not a random pick)",
          (purchase_check["product_id"] == purchase_check["product_id_true"]).all())

    purchase_session_check = purchase_events.merge(
        sessions[["session_id", "customer_id", "anonymous_id"]], on="session_id", suffixes=("", "_sess"))
    order_owner = orders.set_index("order_id")[["customer_id"]]
    purchase_session_check = purchase_session_check.merge(
        order_owner, left_on="order_id", right_index=True, suffixes=("_evt", "_order"))
    known = purchase_session_check[purchase_session_check["customer_id_order"].notna()]
    check("Business rule", "every known-customer purchase event's session genuinely belongs to that "
                          "same customer_id (never mismatched during the order<->session pairing)",
          (known["customer_id_sess"] == known["customer_id_order"]).all())

    # --- 5. Distributional sanity ---
    n_purchase = len(purchase_events)
    n_page_view = (events["event_type"] == "page_view").sum()
    check("Distributional", "page_view is the most common event type by a wide margin "
                          "(browsing dominates the funnel, as in any real site)",
          n_page_view > n_purchase * 5)
    abandon_sessions = events[events["event_type"] == "add_to_cart"]["session_id"]
    converted_sessions = set(purchase_events["session_id"])
    abandon_rate = (~abandon_sessions.isin(converted_sessions)).sum() / sessions["session_id"].nunique()
    # Band centered on the build's own CART_ABANDON_RATE (6% of non-purchase
    # sessions) scaled by the ~88% of sessions that are non-purchase to
    # begin with -- expect roughly 5%, not the tighter 0.5-4% guess this
    # check originally shipped with (that was miscalibrated against the
    # build's actual parameter, not a real data problem).
    check("Distributional", "cart-abandonment (add_to_cart without a purchase in that session) is a small "
                          "single-digit share of all sessions (3-8%)",
          0.03 <= abandon_rate <= 0.08, detail=f"{abandon_rate:.1%}")

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
