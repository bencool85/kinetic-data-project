"""
Phase 3 - orders table (2 of 5, chronologically -- discount_codes came
first). order_type is 'merch' or 'course' only, per schema_reference.md.
Guest checkout (null customer_id + guest_email) is valid ONLY for
order_type='merch' -- automatically true here, since the only source of
guest orders is the anonymous "ghost" population's guest merch purchases
(Phase 0 never gives ghosts a course purchase at all).

Sourced from two places in the master timeline:
1. Known customers' `order_events` (course + merch, from `simulate_customers.py`
   -- already guaranteed course-never-during-a-subscription-window by
   construction there).
2. The anonymous population's one-time guest merch purchases
   (`_sim_anonymous_population.csv`, `is_guest_purchaser` rows) -- these
   customers never get a customer_id at all.

order_id is assigned by GLOBAL chronological order across every known-
customer AND guest order combined (not grouped by customer like most other
tables) -- a real orders table's primary key increments in actual purchase
order across the whole storefront, not per-customer.

Two things invented at this Phase 3 layer (neither exists in the master
timeline, same pattern as billing_interval/past_due in Phase 2):
- `subtotal` (the true pre-discount base price) is reverse-derived from the
  timeline's own `amount` + `subscriber_discount_applied` flag, matched
  against the exact price-tier list and discount formula
  `simulate_customers.py` already used -- not by dividing (amount / 0.8),
  which would risk float drift; matched against the literal known tiers.
- `discount_code_id` / `discount_code_amount`: a share of orders that are
  otherwise eligible (order_date inside the code's valid window,
  applies_to matches order_type, min_order_amount met) get one of
  `discount_codes.csv`'s real codes applied, at ORDER_DISCOUNT_CODE_REDEMPTION_RATE.

Output: data/orders.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED, COURSE_PRICE_TIERS, MERCH_PRICE_TIERS, SUBSCRIBER_MERCH_DISCOUNT, \
    ORDER_DISCOUNT_CODE_REDEMPTION_RATE
from build_customers import customer_id_for, FIRST_NAMES, LAST_NAMES, EMAIL_DOMAINS, EMAIL_DOMAIN_WEIGHTS


def _base_price_from_amount(order_type, amount, discount_applied):
    """Reverse-match the timeline's post-discount amount back to its true
    base price, using the EXACT tier list + formula simulate_customers.py
    used to produce it (round(tier * (1 - SUBSCRIBER_MERCH_DISCOUNT), 2)) --
    not float division, which risks not landing exactly back on a tier."""
    tiers = COURSE_PRICE_TIERS if order_type == "course" else MERCH_PRICE_TIERS
    if not discount_applied:
        return amount
    for tier in tiers:
        if round(tier * (1 - SUBSCRIBER_MERCH_DISCOUNT), 2) == amount:
            return tier
    return amount  # shouldn't happen -- no tier matched


def _eligible_codes(codes, order_type, order_date, subtotal):
    order_date = pd.Timestamp(order_date)
    mask = (
        (codes["valid_from"] <= order_date)
        & (codes["valid_until"].isna() | (codes["valid_until"] >= order_date))
        & (codes["applies_to"].isin(["all", order_type]))
        & (codes["min_order_amount"].isna() | (codes["min_order_amount"] <= subtotal))
    )
    return codes[mask]


def build_orders(seed=SEED + 10):
    rng = np.random.default_rng(seed)
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")
    codes = pd.read_csv("../data/discount_codes.csv")
    codes["valid_from"] = pd.to_datetime(codes["valid_from"])
    codes["valid_until"] = pd.to_datetime(codes["valid_until"])

    raw_orders = []

    for t in timeline:
        customer_id = customer_id_for(t["customer_id"])
        for o in t["order_events"]:
            raw_orders.append({
                "customer_id": customer_id, "guest_email": None,
                "order_type": o["order_type"], "order_date": o["date"], "amount": o["amount"],
                "subscriber_discount_applied": bool(o.get("subscriber_discount_applied", False)),
            })

    used_guest_emails = set()
    guests = anon[anon["is_guest_purchaser"]]
    for row in guests.itertuples():
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        domain = rng.choice(EMAIL_DOMAINS, p=EMAIL_DOMAIN_WEIGHTS)
        base_local = f"{first.lower()}.{last.lower()}"
        email = f"{base_local}@{domain}"
        suffix = 1
        while email in used_guest_emails:
            suffix += 1
            email = f"{base_local}{suffix}@{domain}"
        used_guest_emails.add(email)

        raw_orders.append({
            "customer_id": None, "guest_email": email,
            "order_type": "merch", "order_date": row.guest_purchase_date, "amount": row.guest_purchase_amount,
            "subscriber_discount_applied": False,
        })

    rows = []
    for o in raw_orders:
        subtotal = _base_price_from_amount(o["order_type"], o["amount"], o["subscriber_discount_applied"])
        subscriber_discount_amount = round(subtotal - o["amount"], 2) if o["subscriber_discount_applied"] else 0.0
        price_before_code = o["amount"]

        discount_code_id, discount_code_amount = None, 0.0
        eligible = _eligible_codes(codes, o["order_type"], o["order_date"], subtotal)
        if len(eligible) and rng.random() < ORDER_DISCOUNT_CODE_REDEMPTION_RATE:
            chosen = eligible.sample(n=1, random_state=int(rng.integers(0, 2**31))).iloc[0]
            if chosen["discount_type"] == "percent":
                discount_code_amount = round(price_before_code * chosen["discount_value"] / 100, 2)
            else:
                discount_code_amount = min(chosen["discount_value"], price_before_code)
            discount_code_id = chosen["discount_code_id"]

        total_amount = round(price_before_code - discount_code_amount, 2)

        rows.append({
            "customer_id": o["customer_id"], "guest_email": o["guest_email"],
            "order_type": o["order_type"], "order_date": o["order_date"],
            "subtotal": subtotal,
            "subscriber_discount_applied": o["subscriber_discount_applied"],
            "subscriber_discount_amount": subscriber_discount_amount,
            "discount_code_id": discount_code_id, "discount_code_amount": discount_code_amount,
            "total_amount": total_amount, "currency": "usd",
        })

    df = pd.DataFrame(rows)
    df["order_date"] = pd.to_datetime(df["order_date"])
    # Global chronological order across known-customer AND guest orders alike
    # -- a real order sequence isn't grouped by customer.
    df = df.sort_values("order_date", kind="stable").reset_index(drop=True)
    df.insert(0, "order_id", [f"order_{i+1:06d}" for i in range(len(df))])

    seconds = rng.integers(0, 86400, size=len(df))
    df["created_at"] = (df["order_date"] + pd.to_timedelta(seconds, unit="s")).dt.strftime("%Y-%m-%dT%H:%M:%S")
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")

    return df[["order_id", "customer_id", "guest_email", "order_type", "order_date",
               "subtotal", "subscriber_discount_applied", "subscriber_discount_amount",
               "discount_code_id", "discount_code_amount", "total_amount", "currency", "created_at"]]


if __name__ == "__main__":
    df = build_orders()
    df.to_csv("../data/orders.csv", index=False)
    print(f"Wrote {len(df)} orders\n")
    print(df["order_type"].value_counts().to_string())
    print(f"\nGuest orders (null customer_id): {df['customer_id'].isna().sum()}")
    print(f"Orders with a discount code applied: {df['discount_code_id'].notna().sum()} "
          f"({df['discount_code_id'].notna().mean():.1%})")
    print(f"Total revenue (total_amount): ${df['total_amount'].sum():,.2f}")
