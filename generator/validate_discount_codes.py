"""
Validation for `discount_codes` (Phase 3, table 1 -- built first within the
phase since `orders` needs real codes to redeem against). pandas-based, same
5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

This table has no FKs of its own (it's a standalone reference table -- Phase
7's ad-set tables are the only thing with FKs *into* segments, not here), so
most checks are structural/business-rule around the definitions themselves.
Real usage-based checks (was a code ever redeemed outside its valid window,
actual redemption rate, etc.) belong with `orders`, once it exists.
"""
import datetime
import pandas as pd

from params import START_DATE, END_DATE

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    codes = pd.read_csv("../data/discount_codes.csv")
    codes["valid_from"] = pd.to_datetime(codes["valid_from"])
    codes["valid_until"] = pd.to_datetime(codes["valid_until"])

    # --- 1. Structural ---
    check("Structural", "discount_code_id non-null and unique",
          codes["discount_code_id"].notna().all() and codes["discount_code_id"].is_unique)
    check("Structural", "code non-null and unique (case-insensitive)",
          codes["code"].notna().all() and not codes["code"].str.upper().duplicated().any())
    check("Structural", "discount_type in {percent, fixed_amount}",
          codes["discount_type"].isin(["percent", "fixed_amount"]).all())
    check("Structural", "discount_value > 0 on every code",
          (codes["discount_value"] > 0).all())
    check("Structural", "percent-type discount_value never exceeds 100",
          (codes.loc[codes["discount_type"] == "percent", "discount_value"] <= 100).all())
    check("Structural", "applies_to in {all, merch, course}",
          codes["applies_to"].isin(["all", "merch", "course"]).all())
    check("Structural", "min_order_amount is null or > 0",
          codes["min_order_amount"].dropna().gt(0).all())
    check("Structural", "is_active is boolean", codes["is_active"].isin([True, False]).all())
    check("Structural", "valid_until is null or strictly after valid_from",
          (codes.dropna(subset=["valid_until"])["valid_until"]
           > codes.dropna(subset=["valid_until"])["valid_from"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "no outward FKs from discount_codes at this phase (n/a by design -- standalone reference table)", True)

    # --- 3. Temporal ordering ---
    check("Temporal", "no code's valid_from predates the dataset's START_DATE",
          (codes["valid_from"] >= pd.Timestamp(START_DATE)).all())
    check("Temporal", "is_active is derived correctly from valid_until vs. END_DATE, not hand-picked "
                      "(True iff valid_until is null or >= END_DATE)",
          ((codes["valid_until"].isna() | (codes["valid_until"] >= pd.Timestamp(END_DATE))) == codes["is_active"]).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "at least one evergreen (no-expiry) code exists",
          codes["valid_until"].isna().any())
    check("Business rule", "at least one time-boxed seasonal code exists",
          codes["valid_until"].notna().any())
    check("Business rule", "both discount_type values are represented (not just percent)",
          set(codes["discount_type"]) == {"percent", "fixed_amount"})
    check("Business rule", "more than one applies_to value is represented (not all codes are blanket-'all')",
          codes["applies_to"].nunique() > 1)
    check("Business rule", "no two seasonal codes have overlapping valid windows for the same code family "
                          "(each January promo is its own distinct year, not a duplicate range)",
          not codes.dropna(subset=["valid_until"]).duplicated(subset=["valid_from", "valid_until"]).any())

    # --- 5. Distributional sanity ---
    check("Distributional", "code count is a small, curated list (5-12 codes), not a random-scale table",
          5 <= len(codes) <= 12, f"actual: {len(codes)}")
    pct_values = codes.loc[codes["discount_type"] == "percent", "discount_value"]
    check("Distributional", "percent-type discount values sit in a plausible promotional range (5-30%)",
          pct_values.between(5, 30).all())

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
