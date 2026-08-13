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

# Phase 3 (payments table) -- one Stripe-shaped Charge object per payment
# *attempt*. Every order in orders.csv did eventually succeed (there's no
# abandoned-cart concept in this dataset), but real storefronts see a card
# declined and retried within the same checkout session -- that's the
# realistic messiness modeled here: a share of orders get one or two failed
# charge attempts immediately before the successful one, same order/amount,
# new payment_id + failure_code each time.
PAYMENT_METHOD_WEIGHTS = {"card": 0.86, "paypal": 0.10, "apple_pay": 0.04}
CARD_BRAND_WEIGHTS = {"visa": 0.50, "mastercard": 0.30, "amex": 0.14, "discover": 0.06}
ORDER_PAYMENT_ONE_RETRY_RATE = 0.07   # share of orders with exactly 1 failed attempt before the successful charge
ORDER_PAYMENT_TWO_RETRY_RATE = 0.01   # share of orders with 2 failed attempts before the successful charge (subset, rarer)
PAYMENT_FAILURE_CODE_WEIGHTS = {"card_declined": 0.55, "insufficient_funds": 0.25, "expired_card": 0.12, "processing_error": 0.08}

# Phase 3 (refunds table) -- a share of successful orders later get refunded.
# Most refunds are full; a minority are partial (goodwill/shipping adjustment
# -- these are single-line-item orders, so a partial refund is a discretionary
# adjustment, not a partial-quantity return).
ORDER_REFUND_RATE = 0.045            # of all orders, % that are refunded at some point
PARTIAL_REFUND_SHARE = 0.25          # of refunded orders, % that are partial rather than full
PARTIAL_REFUND_FRACTION_RANGE = (0.20, 0.70)  # partial refund amount, as a fraction of the order total
REFUND_REASON_WEIGHTS = {"requested_by_customer": 0.70, "product_unacceptable": 0.20, "duplicate": 0.05, "fraudulent": 0.05}
REFUND_DELAY_DAYS_RANGE = (1, 21)    # days between order_date and the refund being processed

# =========================================================================
# Phase 7 - Paid media (6 platforms). No user-level joins from ad-platform
# tables to our own data (schema_reference.md) -- attribution only via UTM
# on web_sessions. So these tables are NOT reconciled row-for-row against
# orders/sessions the way Braze was; they're built from the SAME shared
# levers that drove web_sessions' own utm_source volume in the first place
# (_sim_channel_mix_schedule.csv's per-channel weekly share and
# _sim_seasonality_calendar.csv's weekly demand multiplier), so spend/
# impressions/clicks move with the same seasonality and channel-mix shape
# web_sessions already shows -- validated distributionally (correlation),
# not via exact-count reconciliation, since real ad platforms' own
# self-reported numbers never tie out exactly to site-side session counts
# either (that's realistic messiness, not a bug).
PAID_MEDIA_CHANNELS = ["meta", "google_search", "youtube", "dv360", "snap", "tiktok"]

# The 5 objectives, shared vocabulary across all 6 platforms -- matches
# web_sessions.csv's own utm_campaign suffixes (e.g. "meta_retargeting"),
# per generation_plan.md convention #2 (clean channel-level attribution,
# fuzzy campaign-level attribution -- the shipped ad-platform campaign
# names are deliberately more elaborate than the utm_campaign values).
AD_OBJECTIVES = ["prospecting", "retargeting", "lookalike", "conversion", "brand_lift"]
# Retargeting and lookalike objectives target one of segments.csv's 18
# anonymous-grain custom audiences (3 concepts x 6 platforms); prospecting/
# conversion/brand_lift are broad-audience and carry no targeting segment.
AD_OBJECTIVE_TARGETS_SEGMENT = {"prospecting": False, "retargeting": True, "lookalike": True,
                                 "conversion": False, "brand_lift": False}

# Evergreen (always-on) objectives split total daily platform spend by this
# weight; brand_lift is NOT part of this split -- it's a handful of short,
# separately-budgeted awareness flights layered on top (see per-platform
# flight dates), which is how real brand-lift studies actually run.
AD_OBJECTIVE_SPEND_SHARE = {"prospecting": 0.35, "conversion": 0.30, "retargeting": 0.20, "lookalike": 0.15}

# Whole-business average daily paid-media spend (all 6 platforms combined),
# before the channel_mix_schedule split and seasonality multiplier are
# applied. Calibrated loosely against this dataset's scale (860 customers,
# ~2,000-ghost prospecting pool) -- not meant to imply a real CAC benchmark.
BASE_DAILY_AD_SPEND_TOTAL = 950.0
AD_SPEND_NOISE_SD = 0.15          # daily lognormal noise on top of the deterministic seasonality*mix baseline
AD_PAUSE_DAY_RATE = 0.04          # share of active-campaign days with zero delivery (no insights row at all,
                                   # same convention a real ad platform's reporting API uses -- no row, not a zero row)

# --- Meta ---
META_ACCOUNT_ID = "act_10150083647201234"
# Meta's post-2022 "Outcome-Driven Ad Experience" objective enum.
META_OBJECTIVE_BY_AD_OBJECTIVE = {
    "prospecting": "OUTCOME_TRAFFIC", "retargeting": "OUTCOME_SALES", "lookalike": "OUTCOME_SALES",
    "conversion": "OUTCOME_SALES", "brand_lift": "OUTCOME_AWARENESS",
}
# Calibrated to what BASE_DAILY_AD_SPEND_TOTAL's seasonality/channel-mix
# split actually realizes on a typical (non-peak) day for meta's ~24% avg
# channel share, so the declared budget is a believable "typical day" figure
# rather than a number disconnected from realized spend (peak-season days
# legitimately run above it -- real advertisers raise budgets seasonally too).
META_DAILY_BUDGET_CENTS = {"prospecting": 14000, "conversion": 12000, "retargeting": 8000, "lookalike": 6000}
META_BRAND_LIFT_FLIGHTS = [   # (flight start, flight length days, lifetime_budget_cents) -- timed near BFCM each year
    (datetime.date(2023, 11, 13), 18, 350000),
    (datetime.date(2024, 11, 11), 18, 380000),
    (datetime.date(2025, 11, 10), 18, 400000),
]
META_CPM_RANGE_BY_OBJECTIVE = {"prospecting": (8, 14), "retargeting": (10, 18), "lookalike": (9, 15),
                                "conversion": (11, 20), "brand_lift": (4, 8)}
META_CTR_RANGE_BY_OBJECTIVE = {"prospecting": (0.008, 0.015), "retargeting": (0.020, 0.035), "lookalike": (0.012, 0.020),
                                "conversion": (0.010, 0.018), "brand_lift": (0.004, 0.008)}
META_FREQUENCY_RANGE = (1.2, 3.0)
# Conditional funnel rates (each stage as a fraction of the PREVIOUS stage,
# not of link_click) -- guarantees monotonic non-increasing action counts by
# construction: link_click >= landing_page_view >= add_to_cart >=
# initiate_checkout >= purchase.
# Calibrated so SUMMED self-attributed "purchase" actions across all 6
# platforms land within a believable multiple (not 10-20x) of the
# business's actual total real purchases (orders + subscription
# conversions, ~4,200 over the 3-year window) -- ad platforms' own pixels
# genuinely over-claim relative to site-side truth (multi-touch overlap,
# generous attribution windows), but not by an order of magnitude per
# platform, or the sum across 6 platforms would be absurd.
META_ACTION_FUNNEL_BY_OBJECTIVE = {
    "prospecting": {"link_click_rate": 0.90, "to_lpv": 0.75, "to_atc": 0.06, "to_checkout": 0.30, "to_purchase": 0.15},
    "retargeting": {"link_click_rate": 0.94, "to_lpv": 0.85, "to_atc": 0.25, "to_checkout": 0.45, "to_purchase": 0.30},
    "lookalike":   {"link_click_rate": 0.93, "to_lpv": 0.78, "to_atc": 0.13, "to_checkout": 0.40, "to_purchase": 0.25},
    "conversion":  {"link_click_rate": 0.93, "to_lpv": 0.80, "to_atc": 0.16, "to_checkout": 0.45, "to_purchase": 0.25},
    "brand_lift":  {"link_click_rate": 0.85, "to_lpv": 0.50, "to_atc": 0.02, "to_checkout": 0.20, "to_purchase": 0.10},
}
META_VIDEO_VIEW_RATE_BY_OBJECTIVE = {"prospecting": 0.22, "brand_lift": 0.40}  # of impressions, video-forward objectives only

# --- Google Search ---
# Unlike Meta, Search's brand_lift analog (a small always-on branded-term
# defense campaign) is realistically evergreen, not a flighted study -- paying
# a few cents per click to hold the #1 spot on your own brand name never
# pauses. So all 5 objectives are evergreen for this platform, and the
# spend-share dict below carries all 5 keys (sums to 1.0) instead of
# reusing AD_OBJECTIVE_SPEND_SHARE's 4-key evergreen-only version.
GOOGLE_SEARCH_CUSTOMER_ID = "123-456-7890"  # Google Ads' external customer ID format
GOOGLE_SEARCH_OBJECTIVE_SPEND_SHARE = {"prospecting": 0.30, "conversion": 0.35, "retargeting": 0.15,
                                        "lookalike": 0.10, "brand_lift": 0.10}
GOOGLE_SEARCH_DAILY_BUDGET_MICROS = {   # calibrated the same way as META_DAILY_BUDGET_CENTS -- a believable
    "prospecting": 100_000_000, "conversion": 120_000_000, "retargeting": 55_000_000,   # typical-day figure, in
    "lookalike": 35_000_000, "brand_lift": 35_000_000,                                  # micros ($1 = 1,000,000)
}
# Search CTR/CPC run in a very different range than paid social -- much
# higher intent, much higher CTR, and cost is per-click (not CPM-driven).
GOOGLE_SEARCH_CPC_RANGE_BY_OBJECTIVE = {"prospecting": (0.60, 1.40), "retargeting": (0.50, 1.00),
                                         "lookalike": (0.70, 1.30), "conversion": (1.20, 2.50),
                                         "brand_lift": (0.30, 0.70)}
GOOGLE_SEARCH_CTR_RANGE_BY_OBJECTIVE = {"prospecting": (0.020, 0.040), "retargeting": (0.040, 0.080),
                                         "lookalike": (0.030, 0.060), "conversion": (0.050, 0.100),
                                         "brand_lift": (0.080, 0.150)}
GOOGLE_SEARCH_QUALITY_SCORE_RANGE_BY_OBJECTIVE = {"prospecting": (4, 7), "retargeting": (5, 8),
                                                   "lookalike": (5, 8), "conversion": (6, 9), "brand_lift": (8, 10)}
# Conversion rate as a fraction of CLICKS (not a multi-stage funnel like Meta's
# actions array -- Google Ads' own performance tables report a flat
# `conversions` metric directly), calibrated the same way Meta's was: summed
# across the whole platform, self-attributed conversions should land within a
# believable multiple of the business's real total purchases, not 10-20x.
GOOGLE_SEARCH_CONVERSION_RATE_BY_OBJECTIVE = {"prospecting": 0.008, "retargeting": 0.035, "lookalike": 0.015,
                                               "conversion": 0.028, "brand_lift": 0.045}
GOOGLE_SEARCH_AVG_CONVERSION_VALUE_RANGE = (40, 140)  # conversions_value per conversion, loosely AOV-shaped
GOOGLE_SEARCH_MATCH_TYPE_WEIGHTS = {"EXACT": 0.35, "PHRASE": 0.40, "BROAD": 0.25}
GOOGLE_SEARCH_KEYWORDS_PER_AD_GROUP_RANGE = (2, 4)

# --- YouTube (Google Ads, advertising_channel_type == VIDEO) ---
# Structurally mirrors Meta, not Google Search: YouTube's brand_lift is a
# REAL, common measurement product (Google literally sells "YouTube Brand
# Lift" studies run via bumper/non-skippable ad formats), so -- unlike
# Search's always-on brand-term defense -- it's realistically a flighted
# campaign here too, same reasoning as Meta's.
YOUTUBE_CUSTOMER_ID = GOOGLE_SEARCH_CUSTOMER_ID  # same Google Ads account as Search, different channel type
YOUTUBE_AD_FORMAT_BY_OBJECTIVE = {   # advertising_channel_sub_type equivalent
    "prospecting": "VIDEO_TRUE_VIEW_IN_STREAM", "retargeting": "VIDEO_ACTION",
    "lookalike": "VIDEO_TRUE_VIEW_IN_STREAM", "conversion": "VIDEO_ACTION", "brand_lift": "VIDEO_BUMPER",
}
YOUTUBE_BIDDING_STRATEGY_BY_OBJECTIVE = {
    "prospecting": "TARGET_CPV", "retargeting": "MAXIMIZE_CONVERSIONS", "lookalike": "TARGET_CPV",
    "conversion": "MAXIMIZE_CONVERSIONS", "brand_lift": "TARGET_CPM",
}
YOUTUBE_DAILY_BUDGET_MICROS = {"prospecting": 45_000_000, "conversion": 40_000_000,
                                "retargeting": 20_000_000, "lookalike": 15_000_000}
# Flight daily rate calibrated to roughly the SAME proportion of YouTube's
# own (much smaller, ~9%-share) evergreen daily baseline that Meta's flights
# were of Meta's baseline (~1.2x) -- an earlier pass here copied Meta-scale
# dollar figures without rescaling for YouTube's smaller channel share,
# which produced flight-week spend spikes ~4.4x the evergreen baseline
# instead of ~1.2x, badly hurting the spend-vs-seasonality-formula
# correlation check (a real bug, caught by that check, not just cosmetic).
YOUTUBE_BRAND_LIFT_FLIGHTS = [   # (flight start, flight length days, lifetime_budget_micros) -- same BFCM timing as Meta's
    (datetime.date(2023, 11, 13), 18, 2_500_000_000),
    (datetime.date(2024, 11, 11), 18, 2_700_000_000),
    (datetime.date(2025, 11, 10), 18, 2_900_000_000),
]
YOUTUBE_CPV_RANGE_BY_OBJECTIVE = {"prospecting": (0.015, 0.035), "retargeting": (0.020, 0.045),
                                   "lookalike": (0.018, 0.038), "conversion": (0.025, 0.050),
                                   "brand_lift": (0.008, 0.020)}
# video_view_rate = video_views / impressions -- skippable TrueView formats
# run 20-35%; bumper/non-skippable brand_lift ads count nearly every
# impression as a view since the viewer can't skip.
YOUTUBE_VIEW_RATE_RANGE_BY_OBJECTIVE = {"prospecting": (0.20, 0.30), "retargeting": (0.25, 0.35),
                                         "lookalike": (0.22, 0.32), "conversion": (0.25, 0.35),
                                         "brand_lift": (0.90, 0.98)}
YOUTUBE_CLICK_RATE_RANGE_BY_OBJECTIVE = {"prospecting": (0.0010, 0.0030), "retargeting": (0.0030, 0.0060),
                                          "lookalike": (0.0015, 0.0035), "conversion": (0.0030, 0.0060),
                                          "brand_lift": (0.0005, 0.0015)}
# Conversion rate as a fraction of VIDEO_VIEWS (view-through + click
# conversions combined, the way YouTube actually reports them) -- calibrated
# the same "believable single-platform multiple" way as Meta/Search.
YOUTUBE_CONVERSION_RATE_BY_OBJECTIVE = {"prospecting": 0.0005, "retargeting": 0.0026, "lookalike": 0.0009,
                                         "conversion": 0.0021, "brand_lift": 0.00013}
YOUTUBE_AVG_CONVERSION_VALUE_RANGE = (40, 140)

# --- DV360 (Google Programmatic, Display & Video 360) ---
# Genuinely different schema shape than the other 5 platforms
# (schema_reference.md's own callout): real-time bidding across many open-
# web exchanges and environments, not a single owned/operated surface --
# so dv360_performance_daily fragments EACH line_item/day into several
# (exchange, environment) rows rather than one row per line_item/day, the
# way Meta/YouTube/Snap/TikTok do. All 5 objective IOs are evergreen (a
# "reach" / awareness IO on a programmatic platform is a continuous always-
# on buy, not a flighted lift study -- same reasoning as Search's brand-term
# defense, just for a different underlying reason).
DV360_ADVERTISER_ID = "48213097"
DV360_PERFORMANCE_GOAL_BY_OBJECTIVE = {
    "prospecting": "PERFORMANCE_GOAL_TYPE_CPM", "retargeting": "PERFORMANCE_GOAL_TYPE_CPA",
    "lookalike": "PERFORMANCE_GOAL_TYPE_CPM", "conversion": "PERFORMANCE_GOAL_TYPE_CPA",
    "brand_lift": "PERFORMANCE_GOAL_TYPE_VIEWABLE_CPM",
}
DV360_OBJECTIVE_SPEND_SHARE = {"prospecting": 0.30, "conversion": 0.30, "retargeting": 0.15,
                                "lookalike": 0.10, "brand_lift": 0.15}
DV360_DAILY_BUDGET_MICROS = {"prospecting": 30_000_000, "conversion": 30_000_000, "retargeting": 15_000_000,
                              "lookalike": 10_000_000, "brand_lift": 15_000_000}
DV360_LINE_ITEM_TYPE_BY_OBJECTIVE = {   # real DV360 LineItemType enum values
    "prospecting": "LINE_ITEM_TYPE_DISPLAY_DEFAULT", "retargeting": "LINE_ITEM_TYPE_DISPLAY_DEFAULT",
    "lookalike": "LINE_ITEM_TYPE_DISPLAY_DEFAULT", "conversion": "LINE_ITEM_TYPE_DISPLAY_DEFAULT",
    "brand_lift": "LINE_ITEM_TYPE_VIDEO_DEFAULT",
}
DV360_EXCHANGES = ["GOOGLE_AD_MANAGER", "APPNEXUS", "OPENX", "PUBMATIC", "INDEX_EXCHANGE"]
DV360_EXCHANGE_WEIGHTS = [0.40, 0.18, 0.16, 0.14, 0.12]
DV360_ENVIRONMENTS_DISPLAY = ["WEB_OPTIMIZED", "WEB_NOT_OPTIMIZED", "APP"]
DV360_ENVIRONMENTS_DISPLAY_WEIGHTS = [0.55, 0.25, 0.20]
# Video (brand_lift) line items also reach Connected TV inventory -- the
# distinctive DV360 differentiator vs. the other 5 platforms.
DV360_ENVIRONMENTS_VIDEO = ["WEB_OPTIMIZED", "WEB_NOT_OPTIMIZED", "APP", "CONNECTED_TV"]
DV360_ENVIRONMENTS_VIDEO_WEIGHTS = [0.35, 0.15, 0.15, 0.35]
DV360_CPM_RANGE_BY_OBJECTIVE = {"prospecting": (3, 8), "retargeting": (5, 11), "lookalike": (4, 9),
                                 "conversion": (6, 13), "brand_lift": (7, 15)}  # video/CTV CPMs run higher
DV360_CTR_RANGE_BY_OBJECTIVE = {"prospecting": (0.0015, 0.0040), "retargeting": (0.0040, 0.0090),
                                 "lookalike": (0.0020, 0.0050), "conversion": (0.0035, 0.0080),
                                 "brand_lift": (0.0008, 0.0020)}  # open-web display/video CTR runs far below search/social
DV360_CONVERSION_RATE_BY_OBJECTIVE = {"prospecting": 0.006, "retargeting": 0.035, "lookalike": 0.012,
                                       "conversion": 0.025, "brand_lift": 0.004}  # of clicks
DV360_AVG_CONVERSION_VALUE_RANGE = (40, 140)
DV360_EXCHANGE_ENV_COMBOS_PER_DAY_RANGE = (3, 7)  # how many (exchange, environment) rows a line_item/day fragments into
