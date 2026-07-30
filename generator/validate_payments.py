"""
Validation for `payments` (Phase 3, table 4 of 5) -- pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

Central cross-checks: every order_id in orders.csv has EXACTLY one succeeded
payment (never zero, never two -- "this order happened" means exactly one
successful charge in this design) plus zero-or-more failed attempts, all of
which are timestamped strictly before the successful charge; the succeeded
payment's amount matches the order's total_amount exactly; and card
fields are populated if-and-only-if the payment method is "card".
"""
import pandas as pd

from params import SEED
import build_payments as bp

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    payments = pd.read_csv("../data/payments.csv")
    orders = pd.read_csv("../data/orders.csv")
    payments["processed_at"] = pd.to_datetime(payments["processed_at"])

    # --- 1. Structural ---
    check("Structural", "payment_id non-null and unique",
          payments["payment_id"].notna().all() and payments["payment_id"].is_unique)
    check("Structural", "order_id non-null on every row", payments["order_id"].notna().all())
    check("Structural", "amount > 0 on every row", (payments["amount"] > 0).all())
    check("Structural", "status is always 'succeeded' or 'failed'",
          payments["status"].isin(["succeeded", "failed"]).all())
    check("Structural", "failure_code is set iff status == 'failed' (null for succeeded)",
          (payments.loc[payments["status"] == "failed", "failure_code"].notna().all())
          and (payments.loc[payments["status"] == "succeeded", "failure_code"].isna().all()))
    check("Structural", "card_brand/card_last4 populated iff payment_method_type == 'card'",
          (payments.loc[payments["payment_method_type"] == "card", ["card_brand", "card_last4"]].notna().all().all())
          and (payments.loc[payments["payment_method_type"] != "card", ["card_brand", "card_last4"]].isna().all().all()))

    # --- 2. Referential integrity ---
    check("Referential", "every order_id exists in orders.csv", payments["order_id"].isin(orders["order_id"]).all())
    succeeded = payments[payments["status"] == "succeeded"]
    succ_counts = succeeded.groupby("order_id").size()
    check("Referential", "every order_id in orders.csv has EXACTLY one succeeded payment",
          set(succ_counts.index) == set(orders["order_id"]) and (succ_counts == 1).all())

    # --- 3. Temporal ordering ---
    merged = payments.merge(orders[["order_id", "created_at"]], on="order_id", suffixes=("", "_order"))
    merged["created_at_order"] = pd.to_datetime(merged["created_at_order"])
    succ_time = merged[merged["status"] == "succeeded"].set_index("order_id")["processed_at"]
    check("Temporal", "the succeeded payment's processed_at exactly equals its order's created_at",
          (succ_time.sort_index().values == pd.to_datetime(
              orders.set_index("order_id").loc[succ_time.sort_index().index, "created_at"]).values).all())
    failed = merged[merged["status"] == "failed"]
    joined_fail = failed.merge(succ_time.rename("succeeded_at"), on="order_id")
    check("Temporal", "every failed attempt's processed_at is strictly BEFORE its order's successful charge",
          (joined_fail["processed_at"] < joined_fail["succeeded_at"]).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "the succeeded payment's amount matches its order's total_amount exactly",
          succeeded.merge(orders[["order_id", "total_amount"]], on="order_id")
          .pipe(lambda d: (d["amount"].round(2) == d["total_amount"].round(2)).all()))
    check("Business rule", "every failed payment's amount also matches its order's total_amount "
                          "(a retry re-attempts the same charge, not a different amount)",
          payments[payments["status"] == "failed"].merge(orders[["order_id", "total_amount"]], on="order_id")
          .pipe(lambda d: (d["amount"].round(2) == d["total_amount"].round(2)).all()))
    check("Business rule", "currency on every payment row matches its order's currency",
          payments.merge(orders[["order_id", "currency"]], on="order_id", suffixes=("", "_order"))
          .pipe(lambda d: (d["currency"] == d["currency_order"]).all()))
    # customer_id / guest orders: payments.customer_id should be null exactly for guest orders
    cust_check = payments.merge(orders[["order_id", "customer_id"]], on="order_id", suffixes=("", "_order"))
    check("Business rule", "payments.customer_id is null iff the order itself is a guest order (null customer_id)",
          (cust_check["customer_id"].isna() == cust_check["customer_id_order"].isna()).all())

    # --- 5. Distributional sanity ---
    retry_rate = payments[payments["status"] == "failed"]["order_id"].nunique() / orders.shape[0]
    check("Distributional", "share of orders with >=1 failed attempt lands in a realistic single-digit-percent range (3-15%)",
          0.03 <= retry_rate <= 0.15, detail=f"{retry_rate:.1%}")
    method_share = payments["payment_method_type"].value_counts(normalize=True)
    check("Distributional", "card is the dominant payment method (>70% of all attempts)",
          method_share.get("card", 0) > 0.70)

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
