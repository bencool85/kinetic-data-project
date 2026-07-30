"""
Phase 0 - Step 1: Global parameters for the Kinetic synthetic data project.
All downstream generation reads from these constants so the whole dataset
is reproducible from a single seed.
"""
import datetime

SEED = 42

START_DATE = datetime.date(2023, 8, 1)
END_DATE = datetime.date(2026, 7, 30)

N_CUSTOMERS = 100
N_ANONYMOUS = 2000

TRIAL_DAYS = 7

# Pricing
BASIC_MONTHLY = 19.99
BASIC_ANNUAL = 179.00
PLUS_MONTHLY = 34.99

# Behavioral rates (defaults agreed in planning; tune here if needed)
EVER_SUBSCRIBE_RATE = 0.60       # % of the 100 customers who ever start a trial/subscription
TRIAL_CONVERSION_RATE = 0.65     # % of trials that convert to paid
TRIAL_CANCEL_RATE = 0.15         # % of trials actively canceled before trial end
# (remainder, ~0.20, expire passively without canceling)
BASIC_PLAN_SHARE = 0.75          # of those who convert, % choosing Basic vs Plus

GUEST_MERCH_CONVERSION_RATE = 0.08  # % of anonymous ghosts who make a guest merch purchase

# Channel mix at start and end of the date range (interpolated linearly over time)
CHANNEL_MIX_START = {
    "meta": 0.28, "google_search": 0.22, "youtube": 0.08,
    "dv360": 0.08, "snap": 0.08, "tiktok": 0.10, "organic_direct": 0.16,
}
CHANNEL_MIX_END = {
    "meta": 0.20, "google_search": 0.18, "youtube": 0.10,
    "dv360": 0.07, "snap": 0.05, "tiktok": 0.25, "organic_direct": 0.15,
}

# Monthly seasonality multipliers (relative demand for signups/traffic/spend)
MONTHLY_SEASONALITY = {
    1: 1.80,   # January - resolution surge
    2: 1.20,
    3: 1.00,
    4: 0.95,
    5: 0.90,
    6: 0.80,   # summer softness for indoor fitness subscriptions
    7: 0.75,
    8: 0.80,
    9: 1.05,   # back-to-routine bump
    10: 1.00,
    11: 1.30,  # BFCM
    12: 1.10,  # merch gifting, subscriptions cool slightly
}

# Underlying 3-year business growth trend: multiplier grows from 1.0 to this by END_DATE
GROWTH_END_MULTIPLIER = 2.4

# Week-to-week random noise (multiplicative, normal distribution stdev)
WEEKLY_NOISE_STDEV = 0.10
