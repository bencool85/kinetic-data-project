"""
Phase 3 - discount_codes table. Built FIRST within Phase 3, ahead of `orders`
(even though schema_reference.md lists it last) -- orders.discount_code_id
will need real code definitions to redeem against, so this standalone
reference table (no dependencies on anything else) has to exist before
orders can be built, not after. order_line_items/payments/refunds still
depend on orders itself, so this is the correct dependency order even though
it isn't the doc's listing order.

A small, hand-curated list (like products/subscription_plans were), not
randomly generated -- these are business decisions, not simulated behavior.
Mixes evergreen codes (no expiry) with time-boxed seasonal promos, including
two separate one-off January codes in consecutive years (2025 and 2026) --
thematically consistent with the project's already-established January
seasonality (the same demand spike that drives win-back timing).

`is_active` is deliberately NOT an arbitrary flag -- it's derived directly
from `valid_until` vs. END_DATE (the dataset's "today"): a code whose window
has already closed is_active=False by construction, not by hand-picking.
Real redemption-based checks (was a code only ever used inside its valid
window, etc.) get added once `orders` exists and can actually reference
these; only the definitions themselves are checkable today.

Output: data/discount_codes.csv
"""
import datetime
import pandas as pd

from params import START_DATE, END_DATE

# (code, discount_type, discount_value, applies_to, min_order_amount, valid_from, valid_until)
CODES = [
    ("WELCOME10", "percent", 10, "all", None, START_DATE, None),
    ("SAVE15", "percent", 15, "all", 75.00, START_DATE, None),
    ("MERCH25OFF", "fixed_amount", 25.00, "merch", 100.00, START_DATE, None),
    ("COURSE20", "percent", 20, "course", None, START_DATE, None),
    ("HOLIDAY2024", "percent", 20, "all", None, datetime.date(2024, 11, 15), datetime.date(2025, 1, 5)),
    ("JANRESET10_2025", "percent", 10, "all", None, datetime.date(2025, 1, 1), datetime.date(2025, 1, 31)),
    ("JANRESET10_2026", "percent", 10, "all", None, datetime.date(2026, 1, 1), datetime.date(2026, 1, 31)),
]


def build_discount_codes():
    rows = []
    for i, (code, dtype, value, applies_to, min_order, valid_from, valid_until) in enumerate(CODES, start=1):
        is_active = valid_until is None or valid_until >= END_DATE
        rows.append({
            "discount_code_id": f"disc_{i:03d}",
            "code": code,
            "discount_type": dtype,
            "discount_value": value,
            "applies_to": applies_to,
            "min_order_amount": min_order,
            "valid_from": valid_from.isoformat(),
            "valid_until": valid_until.isoformat() if valid_until else None,
            "is_active": is_active,
            "created_at": valid_from.isoformat(),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_discount_codes()
    df.to_csv("../data/discount_codes.csv", index=False)
    print(f"Wrote {len(df)} discount_codes\n")
    print(df.to_string(index=False))
