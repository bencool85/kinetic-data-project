"""
Validation for `refunds` (Phase 3, table 5 of 5, completes Phase 3) --
pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB).

Central cross-checks: every refund's payment_id is genuinely the SUCCEEDED
payment for its order (never a failed attempt); refund.amount <= the
order's total_amount always (the documented "refund <= order total"
convention from generation_plan.md); refunded_at is always after order_date
and on/before END_DATE; and at most one refund per order (no double
refunds in this design).
"""
import datetime
import pandas as pd

from params import SEED, END_DATE
import build_refunds as br

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    refunds = pd.read_csv("../data/refunds.csv")
    orders = pd.read_csv("../data/orders.csv")
    payments = pd.read_csv("../data/payments.csv")

    refunds["refunded_at"] = pd.to_datetime(refunds["refunded_at"])

    # --- 1. Structural ---
    check("Structural", "refund_id non-null and unique",
          refunds["refund_id"].notna().all() and refunds["refund_id"].is_unique)
    check("Structural", "order_id and payment_id non-null on every row",
          refunds[["order_id", "payment_id"]].notna().all().all())
    check("Structural", "amount > 0 on every row", (refunds["amount"] > 0).all())
    check("Structural", "status is always 'succeeded'", (refunds["status"] == "succeeded").all())
    check("Structural", "is_partial is a proper boolean", refunds["is_partial"].isin([True, False]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every order_id exists in orders.csv", refunds["order_id"].isin(orders["order_id"]).all())
    check("Referential", "at most one refund per order (no double refunds in this design)",
          not refunds["order_id"].duplicated().any())
    succeeded_payments = payments[payments["status"] == "succeeded"].set_index("order_id")["payment_id"]
    check("Referential", "every refund's payment_id is genuinely the SUCCEEDED payment for its own order "
                        "(never a failed attempt, never a different order's payment)",
          refunds.apply(lambda r: succeeded_payments.get(r["order_id"]) == r["payment_id"], axis=1).all())

    # --- 3. Temporal ordering ---
    joined = refunds.merge(orders[["order_id", "order_date"]], on="order_id")
    joined["order_date"] = pd.to_datetime(joined["order_date"])
    check("Temporal", "refunded_at is always strictly after the order's own order_date",
          (joined["refunded_at"] > joined["order_date"]).all())
    # Compared at DATE granularity, matching how END_DATE is used as a boundary
    # everywhere else in this project (e.g. devices.py's last_seen_at) -- a
    # refund timestamped at noon on END_DATE itself is still "on or before
    # END_DATE", not after it; only the calendar date matters here, not the
    # time-of-day component build_refunds.py happens to assign.
    check("Temporal", "refunded_at's calendar date never falls after END_DATE (the dataset's own observation window)",
          (joined["refunded_at"].dt.date <= END_DATE).all())

    # --- 4. Business-rule invariants ---
    amt_check = refunds.merge(orders[["order_id", "total_amount"]], on="order_id")
    check("Business rule", "refund.amount never exceeds its order's total_amount (refund <= order total)",
          (amt_check["amount"] <= amt_check["total_amount"] + 1e-9).all())
    full_refunds = amt_check[~refunds.set_index("order_id").loc[amt_check["order_id"], "is_partial"].values]
    check("Business rule", "every non-partial refund's amount exactly equals the order's total_amount",
          (full_refunds["amount"].round(2) == full_refunds["total_amount"].round(2)).all())
    partial_refunds = amt_check[refunds.set_index("order_id").loc[amt_check["order_id"], "is_partial"].values]
    check("Business rule", "every partial refund's amount is strictly LESS than the order's total_amount",
          (partial_refunds["amount"] < partial_refunds["total_amount"]).all())
    check("Business rule", "currency on every refund matches its order's currency",
          refunds.merge(orders[["order_id", "currency"]], on="order_id", suffixes=("", "_order"))
          .pipe(lambda d: (d["currency"] == d["currency_order"]).all()))
    cust_check = refunds.merge(orders[["order_id", "customer_id"]], on="order_id", suffixes=("", "_order"))
    check("Business rule", "refunds.customer_id is null iff the order itself is a guest order",
          (cust_check["customer_id"].isna() == cust_check["customer_id_order"].isna()).all())

    # --- 5. Distributional sanity ---
    refund_rate = len(refunds) / len(orders)
    check("Distributional", "overall refund rate lands in a realistic low-single-digit-percent range (2-7%)",
          0.02 <= refund_rate <= 0.07, detail=f"{refund_rate:.1%}")
    partial_share = refunds["is_partial"].mean()
    check("Distributional", "partial-refund share roughly matches the configured 25% (15-35% band)",
          0.15 <= partial_share <= 0.35, detail=f"{partial_share:.1%}")

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
