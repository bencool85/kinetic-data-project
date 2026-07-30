"""
Validation for `orders` (Phase 3, table 2 -- discount_codes came first).
pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB).

The central cross-check this table needs that no earlier table could even
attempt: confirming "no course order during an active subscription" against
subscriptions.csv itself (a genuinely independent, already-shipped table),
not just re-trusting that the master timeline's own generation logic avoided
it. This is the first table built after Phase 2, so it's the first real
chance to catch a Phase 2/Phase 0 drift if one existed.
"""
import datetime
import json
import pandas as pd

from params import COURSE_PRICE_TIERS, MERCH_PRICE_TIERS, SUBSCRIBER_MERCH_DISCOUNT, \
    ORDER_DISCOUNT_CODE_REDEMPTION_RATE

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    orders = pd.read_csv("../data/orders.csv")
    customers = pd.read_csv("../data/customers.csv")
    subs = pd.read_csv("../data/subscriptions.csv")
    codes = pd.read_csv("../data/discount_codes.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")

    orders["order_date"] = pd.to_datetime(orders["order_date"])
    subs["start_date"] = pd.to_datetime(subs["start_date"])
    subs["canceled_at"] = pd.to_datetime(subs["canceled_at"])
    subs["trial_start"] = pd.to_datetime(subs["trial_start"])
    codes["valid_from"] = pd.to_datetime(codes["valid_from"])
    codes["valid_until"] = pd.to_datetime(codes["valid_until"])

    # --- 1. Structural ---
    check("Structural", "order_id non-null and unique",
          orders["order_id"].notna().all() and orders["order_id"].is_unique)
    check("Structural", "order_type in {merch, course}", orders["order_type"].isin(["merch", "course"]).all())
    check("Structural", "customer_id populated XOR guest_email populated (never both, never neither)",
          (orders["customer_id"].notna() != orders["guest_email"].notna()).all())
    check("Structural", "subtotal, subscriber_discount_amount, discount_code_amount, total_amount all >= 0",
          (orders[["subtotal", "subscriber_discount_amount", "discount_code_amount", "total_amount"]] >= 0).all().all())
    check("Structural", "total_amount == subtotal - subscriber_discount_amount - discount_code_amount exactly",
          (orders["total_amount"].round(2) ==
           (orders["subtotal"] - orders["subscriber_discount_amount"] - orders["discount_code_amount"]).round(2)).all())
    check("Structural", "discount_code_id populated if and only if discount_code_amount > 0",
          (orders["discount_code_id"].notna() == (orders["discount_code_amount"] > 0)).all())
    check("Structural", "subscriber_discount_amount > 0 if and only if subscriber_discount_applied is True",
          ((orders["subscriber_discount_amount"] > 0) == orders["subscriber_discount_applied"]).all())
    check("Structural", "currency is always 'usd'", (orders["currency"] == "usd").all())

    # --- 2. Referential integrity ---
    check("Referential", "every non-null customer_id exists in customers.csv",
          orders["customer_id"].dropna().isin(customers["customer_id"]).all())
    check("Referential", "every non-null discount_code_id exists in discount_codes.csv",
          orders["discount_code_id"].dropna().isin(codes["discount_code_id"]).all())
    check("Referential", "guest checkout (null customer_id) occurs ONLY on order_type='merch' "
                        "(per schema_reference.md's business rule)",
          (orders.loc[orders["customer_id"].isna(), "order_type"] == "merch").all())
    check("Referential", "every order_type='course' row has a non-null customer_id (never a guest)",
          orders.loc[orders["order_type"] == "course", "customer_id"].notna().all())

    # --- 3. Temporal ordering ---
    # THE central cross-check: no course order falls inside an active
    # subscription window, verified against subscriptions.csv itself (an
    # independently-built, already-shipped table) -- not just re-trusting
    # the timeline's own generation logic.
    # Only rows representing a REAL (post-conversion) subscription interval
    # grant the "full catalog access" that blocks a course purchase -- a bare
    # trial does NOT (the master timeline's own active_subscription_windows()
    # is built only from `subscription_intervals`, which starts at trial_end,
    # never from the trial itself). Distinguishing a trial-only subscription
    # object from a real interval using only subscriptions.csv's shipped
    # columns (interval_id is intentionally internal-only): a trial-only
    # object's start_date exactly equals its own trial_start; a real
    # converted interval's start_date is trial_end instead (and a win-back
    # resubscribe has no trial_start at all).
    real_interval_subs = subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])]
    windows_by_customer = {}
    for row in real_interval_subs.itertuples():
        end = row.canceled_at if pd.notna(row.canceled_at) else pd.Timestamp(datetime.date(2026, 7, 30))
        windows_by_customer.setdefault(row.customer_id, []).append((row.start_date, end))

    violations = 0
    course_orders = orders[orders["order_type"] == "course"]
    for row in course_orders.itertuples():
        for start, end in windows_by_customer.get(row.customer_id, []):
            if start <= row.order_date <= end:
                violations += 1
                break
    check("Temporal", "NO course order falls within any of its customer's active subscription windows, "
                      "cross-checked against subscriptions.csv directly (not the internal timeline)",
          violations == 0, f"{violations} violating course orders out of {len(course_orders)}")

    check("Temporal", "every discount_code_id used on an order was actually valid (order_date within "
                      "the code's window) on that order's own date",
          orders.dropna(subset=["discount_code_id"]).merge(
              codes[["discount_code_id", "valid_from", "valid_until"]], on="discount_code_id"
          ).pipe(lambda d: (
              (d["order_date"] >= d["valid_from"]) &
              (d["valid_until"].isna() | (d["order_date"] <= d["valid_until"]))
          ).all()))

    # --- 4. Business-rule invariants ---
    check("Business rule", "subtotal always matches a real product-catalog price tier "
                          "(COURSE_PRICE_TIERS for course, MERCH_PRICE_TIERS for merch)",
          orders.loc[orders["order_type"] == "course", "subtotal"].isin(COURSE_PRICE_TIERS).all()
          and orders.loc[orders["order_type"] == "merch", "subtotal"].isin(MERCH_PRICE_TIERS).all())

    check("Business rule", "subscriber_discount_applied is never True on a course order "
                          "(the discount only ever applies to merch)",
          not orders.loc[orders["order_type"] == "course", "subscriber_discount_applied"].any())

    check("Business rule", "guest orders (no customer_id) never have subscriber_discount_applied=True "
                          "(a guest, by definition, is never a subscriber)",
          not orders.loc[orders["customer_id"].isna(), "subscriber_discount_applied"].any())

    check("Business rule", "wherever subscriber_discount_applied is True, subscriber_discount_amount "
                          "matches the exact 20% formula (round(subtotal * 0.20, 2))",
          (orders.loc[orders["subscriber_discount_applied"], "subscriber_discount_amount"] ==
           (orders.loc[orders["subscriber_discount_applied"], "subtotal"] * SUBSCRIBER_MERCH_DISCOUNT).round(2)).all())

    check("Business rule", "every discount_code_amount matches its code's own stated discount formula "
                          "(percent-of-price or flat amount, capped at the price)",
          orders.dropna(subset=["discount_code_id"]).merge(
              codes[["discount_code_id", "discount_type", "discount_value"]], on="discount_code_id"
          ).assign(price_before_code=lambda d: d["subtotal"] - d["subscriber_discount_amount"])
          .pipe(lambda d: (
              d["discount_code_amount"].round(2) == d.apply(
                  lambda r: round(r["price_before_code"] * r["discount_value"] / 100, 2)
                  if r["discount_type"] == "percent" else min(r["discount_value"], r["price_before_code"]),
                  axis=1).round(2)
          ).all()))

    # Exact row-count reconciliation against source data (timeline + anon population)
    n_course_expected = sum(1 for t in timeline for o in t["order_events"] if o["order_type"] == "course")
    n_merch_customer_expected = sum(1 for t in timeline for o in t["order_events"] if o["order_type"] == "merch")
    n_guest_expected = int(anon["is_guest_purchaser"].sum())
    expected_total = n_course_expected + n_merch_customer_expected + n_guest_expected
    check("Business rule", "total order count exactly reconciles against the timeline's order_events "
                          "plus the anonymous population's guest purchases",
          len(orders) == expected_total,
          f"{len(orders)} orders vs. {n_course_expected} course + {n_merch_customer_expected} customer-merch "
          f"+ {n_guest_expected} guest = {expected_total}")

    check("Business rule", "guest order count exactly matches the anonymous population's is_guest_purchaser count",
          orders["customer_id"].isna().sum() == n_guest_expected)

    # --- 5. Distributional sanity ---
    redemption_rate = orders["discount_code_id"].notna().mean()
    check("Distributional", f"discount code redemption rate ~{ORDER_DISCOUNT_CODE_REDEMPTION_RATE:.0%} (within 3pp)",
          abs(redemption_rate - ORDER_DISCOUNT_CODE_REDEMPTION_RATE) < 0.03, f"actual: {redemption_rate:.1%}")

    check("Distributional", "total recognized order revenue is a plausible positive figure for this dataset's scale",
          0 < orders["total_amount"].sum() < 2_000_000, f"${orders['total_amount'].sum():,.2f}")

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
