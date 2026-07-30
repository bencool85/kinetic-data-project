"""
Phase 0 - Step 1: Global parameters for the Kinetic synthetic data project.
All downstream generation reads from these constants so the whole dataset
is reproducible from a single seed.
"""
import datetime

SEED = 42

START_DATE = datetime.date(2023, 8, 1)
END_DATE = datetime.date(2026, 7, 30)

N_CUSTOMERS = 860        # derived: sized so ~100 subscribers land active as of END_DATE
                         # (re-derived after adding the email-to-subscriber pathway, which
                         # adds active subscribers beyond the original 1,100-customer calibration)
N_ANONYMOUS = 17050      # scaled proportionally with N_CUSTOMERS

TRIAL_DAYS = 7

# Pricing
BASIC_MONTHLY = 19.99
BASIC_ANNUAL = 179.00
PLUS_MONTHLY = 34.99
PLUS_ANNUAL = 314.00     # ~25.4% off monthly-equivalent, same discount ratio as Basic
                          # (Basic: 179.00 / (19.99*12) = 74.6% of monthly-equivalent)

# Behavioral rates (defaults agreed in planning; tune here if needed)
EVER_SUBSCRIBE_RATE = 0.60       # % of all customers who ever start a trial/subscription
TRIAL_CONVERSION_RATE = 0.30     # % of trials that convert to paid (lowered from 0.65 - "too high")
TRIAL_CANCEL_RATE = 0.15         # % of trials actively canceled before trial end
# (remainder, ~0.55, expire passively without canceling -- mechanically larger now
# that conversion dropped and the cancel rate held fixed)
BASIC_PLAN_SHARE = 0.75          # of those who convert, % choosing Basic vs Plus

GUEST_MERCH_CONVERSION_RATE = 0.08  # % of anonymous ghosts who make a guest merch purchase

# Subscription lifecycle (Phase 0 Step 5) -- two-segment churn model.
# A single constant churn rate can't hit "40% annual retention" AND "avg churner
# tenure = 3 months" simultaneously (a constant hazard is memoryless: those two
# numbers are mechanically linked). Instead: some subscribers essentially never
# organically churn ("loyal"), and the rest churn fast ("quick", ~3mo average).
# Blended, this gives ~40% annual retention while nearly all *realized* churns
# come from the quick segment, landing its average tenure right at ~3 months.
LOYAL_SEGMENT_SHARE = 0.3888           # solved so blended annual retention = 40%
QUICK_CHURN_MEAN_TENURE_MONTHS = 3.0    # mean tenure for the "quick churn" segment
PLAN_CHANGE_PROBABILITY = 0.20         # chance of one upgrade/downgrade mid-interval
INVOLUNTARY_CHURN_SHARE = 0.25         # of quick-segment churns, fraction via payment failure
WINBACK_PROBABILITY = 0.25             # chance a churned (quick-segment) subscriber eventually resubscribes
# Win-back timing: reuse the seasonality calendar's weekly multiplier (same mechanism
# as signup dates) so reactivations cluster around January every year -- total
# subscribers peak in January and taper through the rest of the year, same as new
# signups. A minimum gap is enforced so nobody reactivates in the same month they churned.
WINBACK_MIN_GAP_MONTHS = 1
PAYMENT_BLIP_PROBS = {0: 0.75, 1: 0.20, 2: 0.05}  # resolved payment-failure blips per interval
REACTIVATION_CHANNEL_WEIGHTS = {"email": 0.50, "push": 0.15, "organic": 0.35}
LAPSED_STILL_BUYING_RATE = 0.10        # of currently-lapsed subscribers, % who still buy courses/merch since lapsing (down from 0.30)

# Phase 2 (subscriptions table) -- billing_interval isn't part of the Phase 0
# master timeline (only plan *tier* is), so it's assigned here, once per
# subscription object, at build time. This is also what resolves the
# long-flagged "billing_interval isn't in the master timeline" gap (see
# generation_plan.md's Cross-phase consistency commitments).
ANNUAL_BILLING_SHARE = 0.20      # of subscriptions, % that choose annual over monthly billing
# Past_due is a Stripe dunning-grace-period status: a renewal payment attempt
# just failed but the subscription hasn't been canceled (yet) -- also not in
# the master timeline (Phase 0 only models payment failures as either
# instantly-resolved noise or an immediate involuntary churn), so it's layered
# on at build time for a small share of subscriptions that just renewed.
PAST_DUE_RATE = 0.06             # of recently-renewed active subscriptions, % currently in a payment-failure grace period
PAST_DUE_WINDOW_DAYS = 14         # "recently renewed" = current_period_start within this many days of END_DATE

# Phase 2 (subscription_events table) -- realistic messiness explicitly called
# out in schema_reference.md's intro ("duplicate webhook-style events"): Stripe
# webhooks are at-least-once delivery, so a real ingestion pipeline sees the
# exact same event redelivered occasionally. A small share of events get a
# byte-for-byte duplicate row (same subscription/type/timestamp, new event_id).
DUPLICATE_WEBHOOK_RATE = 0.03

# Phase 3 (orders table) -- discount codes don't exist anywhere in the master
# timeline (Phase 0 never modeled promo codes), so redemption is layered on
# at build time: a share of otherwise-eligible orders (valid code window,
# matching applies_to, min_order_amount met) get one applied.
ORDER_DISCOUNT_CODE_REDEMPTION_RATE = 0.12

# New acquisition pathway: a course/merch-only customer (never subscribed) who
# eventually receives a targeted "come try a membership" email based on their own
# purchase history and starts a trial because of it. Timing is relative to their
# purchase history, not the seasonal calendar -- a warm, triggered send, not a
# calendar campaign.
MERCH_TO_SUB_EMAIL_RATE = 0.175              # % of course/merch-only customers this eventually reaches (target range 15-20%)
MERCH_TO_SUB_TRIAL_CONVERSION_RATE = 0.475   # trial-to-paid rate for this warm pathway (target range 45-50%, vs 30% baseline)
MERCH_TO_SUB_TRIGGER_GAP_MONTHS_RANGE = (3, 12)  # months after their first course/merch order that the email lands

# Order behavior
COURSE_ORDERS_PER_YEAR_NONSUB_RANGE = (1, 4)  # course/merch-only accounts, per active year
MERCH_ORDERS_PER_YEAR_RANGE = (0, 3)           # any account, per active year
COURSE_PRICE_TIERS = [9.99, 79.00, 99.00, 129.00, 149.00]
COURSE_PRICE_WEIGHTS = [0.45, 0.20, 0.15, 0.12, 0.08]
MERCH_PRICE_TIERS = [24.99, 34.99, 49.99, 64.99, 89.99, 120.00]
MERCH_PRICE_WEIGHTS = [0.25, 0.25, 0.20, 0.15, 0.10, 0.05]
SUBSCRIBER_MERCH_DISCOUNT = 0.20        # 20% off for active subscribers

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

# Phase 1 - customers table
EMAIL_OPT_IN_RATE = 0.88   # opted into marketing email at signup (high -- it's how they signed up)
PUSH_OPT_IN_RATE = 0.45    # opted into push notifications (lower -- requires a separate device permission grant)
IS_DELETED_RATE = 0.02     # soft-deleted accounts (GDPR-style request); PII scrubbed, customer_id and
                           # historical rows (orders/subscriptions/etc.) are preserved for referential integrity

# Phase 1 - devices table
SECOND_DEVICE_RATE = 0.20   # of non-deleted customers, % who also have a 2nd device on file
DEVICE_TYPE_WEIGHTS = {"ios": 0.45, "android": 0.35, "web": 0.20}  # fitness app skews mobile
