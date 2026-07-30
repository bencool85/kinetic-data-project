"""
Phase 0 - Step 4: The anonymous "ghost" population — visitors who never become one
of the 100 tracked customers. A small slice convert straight to a guest merch
purchase without ever creating an account; this is the sole source of guest
checkouts in the eventual `orders` table.

Output: internal/_sim_anonymous_population.csv
"""
import datetime
import uuid
import numpy as np
import pandas as pd

from params import SEED, N_ANONYMOUS, GUEST_MERCH_CONVERSION_RATE, END_DATE
from sim_utils import load_calendar, load_channel_mix, sample_weighted_date, sample_channel

MERCH_PRICE_TIERS = [24.99, 34.99, 49.99, 64.99, 89.99, 120.00]
MERCH_PRICE_WEIGHTS = [0.25, 0.25, 0.20, 0.15, 0.10, 0.05]


def build_anonymous_population(seed=SEED + 1):
    rng = np.random.default_rng(seed)
    calendar = load_calendar()
    channel_mix = load_channel_mix()

    rows = []
    for _ in range(N_ANONYMOUS):
        anon_id = "anon_" + uuid.uuid4().hex[:16]
        first_seen = sample_weighted_date(calendar, rng)
        channel = sample_channel(channel_mix, rng, first_seen)
        num_sessions = int(rng.choice([1, 2, 3], p=[0.70, 0.22, 0.08]))

        is_guest_purchaser = bool(rng.random() < GUEST_MERCH_CONVERSION_RATE)
        purchase_date_str, purchase_amount = "", ""
        if is_guest_purchaser:
            days_to_purchase = int(rng.integers(0, 14))
            purchase_date = first_seen + datetime.timedelta(days=days_to_purchase)
            if purchase_date > END_DATE:
                purchase_date = END_DATE
            purchase_date_str = purchase_date.isoformat()
            purchase_amount = round(float(rng.choice(MERCH_PRICE_TIERS, p=MERCH_PRICE_WEIGHTS)), 2)

        rows.append({
            "anonymous_id": anon_id,
            "first_seen_date": first_seen.isoformat(),
            "channel": channel,
            "num_sessions": num_sessions,
            "is_guest_purchaser": is_guest_purchaser,
            "guest_purchase_date": purchase_date_str,
            "guest_purchase_amount": purchase_amount,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_anonymous_population()
    df.to_csv("../internal/_sim_anonymous_population.csv", index=False)
    print(f"Generated {len(df)} anonymous visitors")
    print(f"Guest purchasers: {df['is_guest_purchaser'].sum()} "
          f"({df['is_guest_purchaser'].mean()*100:.1f}%)")
    print("\nChannel distribution:")
    print(df["channel"].value_counts(normalize=True).round(3).to_string())
    print("\nSession count distribution:")
    print(df["num_sessions"].value_counts(normalize=True).round(3).to_string())
