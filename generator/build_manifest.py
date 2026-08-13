"""
Builds/refreshes File_Manifest.xlsx at the project root — a running log of every
file committed to Ben's synced folder, with a description and last-updated timestamp.
Re-run this (with updated FILES list) any time files are added or edited.
"""
import os
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

PROJECT_ROOT = "/home/claude/kinetic-project"
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "File_Manifest.xlsx")

# (relative file path, category, description)
FILES = [
    ("README.md", "Docs", "Project overview and folder structure guide"),
    ("CHANGELOG.md", "Docs", "Plain-English log of every decision and build step"),
    ("docs/business_context.md", "Docs", "Kinetic business model: subscriptions, courses, merch, seasonality"),
    ("docs/schema_reference.md", "Docs", "Full 47-table schema reference across all domains"),
    ("docs/generation_plan.md", "Docs", "Build sequence, validation approach, canonical metrics, locked conventions"),
    ("generator/params.py", "Code", "Phase 0 Step 1: global constants (scale, dates, pricing, rates)"),
    ("generator/build_calendar.py", "Code", "Phase 0 Steps 2-3: builds seasonality calendar + channel mix schedule"),
    ("generator/build_manifest.py", "Code", "Builds/refreshes this file manifest spreadsheet"),
    ("internal/_sim_seasonality_calendar.csv", "Internal artifact", "Weekly demand multiplier driving signups/spend/traffic"),
    ("internal/_sim_channel_mix_schedule.csv", "Internal artifact", "Acquisition channel share over time (Meta/Google/YouTube/DV360/Snap/TikTok/organic)"),
    ("internal/seasonality_preview.png", "Chart", "Visual sanity-check of the seasonality calendar"),
    (".gitignore", "Repo config", "Excludes Python __pycache__ from git/sync"),
    ("File_Manifest.xlsx", "Docs", "This file — running log of every file committed to the folder"),
    ("generator/sim_utils.py", "Code", "Shared weighted date/channel sampling helpers"),
    ("generator/build_anonymous_population.py", "Code", "Phase 0 Step 4: builds the ~2,000-person anonymous ghost population (anon_id now hash-derived, not uuid4 -- reproducibility fix)"),
    ("generator/simulate_customers.py", "Code", "Phase 0 Steps 5-6: per-customer master timeline + attribution ground truth (fixed: course_merch_only orders now reconciled against the eventual subscription window; pre_signup_anon_id now hash-derived, not uuid4)"),
    ("internal/_sim_anonymous_population.csv", "Internal artifact", "Anonymous visitors who never become tracked customers; source of guest merch orders"),
    ("internal/_sim_customer_timeline.json", "Internal artifact", "Full nested ground-truth simulation for all 100 customers (signup, trial, subscriptions, orders, churn)"),
    ("internal/_sim_customer_timeline_summary.csv", "Internal artifact", "Flattened, spreadsheet-readable summary of the customer timeline"),
    ("internal/_sim_attribution_ground_truth.json", "Internal artifact", "True acquisition/reactivation channel per customer, kept separate from intentionally messy shipped UTM data"),
    ("generator/build_simulation_charts.py", "Code", "Builds the funnel + segment breakdown charts for the simulation analysis"),
    ("internal/funnel_chart.png", "Chart", "Customer funnel: total -> trial started -> converted -> active today"),
    ("internal/segment_breakdown_chart.png", "Chart", "Part-to-whole breakdown of all customers' current status"),
    ("docs/phase0_simulation_analysis.md", "Docs", "Summary analysis of the recalibrated Phase 0 simulation results"),
    ("generator/build_products.py", "Code", "Phase 1: builds the products table (~12-item course/merch catalog)"),
    ("generator/validate_products.py", "Code", "Phase 1: 5-layer validation for products (structural/referential/temporal/business-rule/distributional)"),
    ("data/products.csv", "Shipped table", "Phase 1: products table (course + merch catalog)"),
    ("generator/build_product_variants.py", "Code", "Phase 1: builds product_variants (sizes for apparel, single variant elsewhere)"),
    ("generator/validate_product_variants.py", "Code", "Phase 1: 5-layer validation for product_variants, including FK to products"),
    ("data/product_variants.csv", "Shipped table", "Phase 1: product_variants table (21 variants across 12 products)"),
    ("generator/build_subscription_plans.py", "Code", "Phase 1: builds subscription_plans (Basic/Plus x monthly/annual)"),
    ("generator/validate_subscription_plans.py", "Code", "Phase 1: 5-layer validation for subscription_plans"),
    ("data/subscription_plans.csv", "Shipped table", "Phase 1: subscription_plans table (4 plans)"),
    ("generator/build_customers.py", "Code", "Phase 1: builds customers table from the master timeline; defines customer_id mapping"),
    ("generator/validate_customers.py", "Code", "Phase 1: 5-layer validation for customers, incl. 1:1 reconciliation vs. the timeline"),
    ("data/customers.csv", "Shipped table", "Phase 1: customers table (860 rows, one per simulated customer)"),
    ("generator/build_customer_addresses.py", "Code", "Phase 1: builds customer_addresses (billing/shipping, obviously-fake streets)"),
    ("generator/validate_customer_addresses.py", "Code", "Phase 1: 5-layer validation for customer_addresses"),
    ("data/customer_addresses.csv", "Shipped table", "Phase 1: customer_addresses table (1,431 rows)"),
    ("generator/build_devices.py", "Code", "Phase 1: builds devices (customer + anonymous-ghost devices; 2nd-device anon_id now hash-derived, not uuid4)"),
    ("generator/validate_devices.py", "Code", "Phase 1: 5-layer validation for devices"),
    ("data/devices.csv", "Shipped table", "Phase 1: devices table (18,042 rows: known-customer + ghost devices)"),
    ("generator/build_identity_map.py", "Code", "Phase 1: builds identity_map (anonymous_id -> customer_id resolution events)"),
    ("generator/validate_identity_map.py", "Code", "Phase 1: 5-layer validation for identity_map"),
    ("data/identity_map.csv", "Shipped table", "Phase 1: identity_map table (992 rows)"),
    ("generator/build_segments.py", "Code", "Phase 1: builds segments (27 definitions: 9 customer-grain, 18 anonymous -- 3 audience concepts x 6 ad platforms)"),
    ("generator/validate_segments.py", "Code", "Phase 1: 5-layer validation for segments"),
    ("data/segments.csv", "Shipped table", "Phase 1: segments table (27 rows) -- completes Phase 1 (all 8 tables)"),
    ("generator/build_subscriptions.py", "Code", "Phase 2: builds subscriptions (Stripe-shaped subscription objects; assigns billing_interval + next-renewal date, resolving the long-flagged Phase 2 gap)"),
    ("generator/validate_subscriptions.py", "Code", "Phase 2: 5-layer validation for subscriptions"),
    ("data/subscriptions.csv", "Shipped table", "Phase 2: subscriptions table (576 rows: one Stripe-shaped subscription object per trial-or-interval)"),
    ("generator/build_subscription_events.py", "Code", "Phase 2: builds subscription_events (event log behind every subscription: trial_started/converted/expired, renewed, upgraded/downgraded, payment_failed, canceled, resumed)"),
    ("generator/validate_subscription_events.py", "Code", "Phase 2: 5-layer validation for subscription_events"),
    ("data/subscription_events.csv", "Shipped table", "Phase 2: subscription_events table (2,423 rows, incl. ~3% deliberate duplicate webhook-style rows)"),
    ("generator/build_invoices.py", "Code", "Phase 2: builds invoices (one per initial charge + renewal, plus uncollectible/open for failed payments) -- completes Phase 2 (all 3 tables)"),
    ("generator/validate_invoices.py", "Code", "Phase 2: 5-layer validation for invoices"),
    ("data/invoices.csv", "Shipped table", "Phase 2: invoices table (1,229 rows) -- completes Phase 2"),
    ("generator/build_discount_codes.py", "Code", "Phase 3: builds discount_codes (hand-curated list: evergreen + seasonal promo codes) -- built first in Phase 3 since orders needs it"),
    ("generator/validate_discount_codes.py", "Code", "Phase 3: 5-layer validation for discount_codes"),
    ("data/discount_codes.csv", "Shipped table", "Phase 3: discount_codes table (7 rows)"),
    ("generator/build_orders.py", "Code", "Phase 3: builds orders (customer course/merch + guest merch), cross-validated against subscriptions.csv"),
    ("generator/validate_orders.py", "Code", "Phase 3: 5-layer validation for orders, incl. the no-course-during-subscription cross-check"),
    ("data/orders.csv", "Shipped table", "Phase 3: orders table (3,650 rows: 1,061 course + 1,332 customer-merch + 1,257 guest-merch)"),
    ("generator/build_order_line_items.py", "Code", "Phase 3: builds order_line_items (one row per order -- resolves each order's price tier down to a specific product + variant)"),
    ("generator/validate_order_line_items.py", "Code", "Phase 3: 5-layer validation for order_line_items"),
    ("data/order_line_items.csv", "Shipped table", "Phase 3: order_line_items table (3,650 rows, one per order)"),
    ("generator/build_payments.py", "Code", "Phase 3: builds payments (one Stripe-shaped Charge attempt per row; models realistic declined-then-retried charge attempts)"),
    ("generator/validate_payments.py", "Code", "Phase 3: 5-layer validation for payments"),
    ("data/payments.csv", "Shipped table", "Phase 3: payments table (3,964 rows: 3,650 succeeded + 314 failed retry attempts)"),
    ("generator/build_refunds.py", "Code", "Phase 3: builds refunds (against a small share of orders' succeeded payments) -- completes Phase 3 (all 5 tables)"),
    ("generator/validate_refunds.py", "Code", "Phase 3: 5-layer validation for refunds"),
    ("data/refunds.csv", "Shipped table", "Phase 3: refunds table (159 rows, 4.4% of orders) -- completes Phase 3"),
    ("generator/build_customer_segment_membership.py", "Code", "Phase 4: builds customer_segment_membership (effective-dated, derived entirely from subscriptions/orders/invoices -- seg_009 skipped, needs Phase 5) -- completes Phase 4"),
    ("generator/validate_customer_segment_membership.py", "Code", "Phase 4: 5-layer validation for customer_segment_membership"),
    ("data/customer_segment_membership.csv", "Shipped table", "Phase 4: customer_segment_membership table (2,234 rows across 8 of 9 customer-grain segments) -- completes Phase 4"),
    ("generator/build_web_sessions.py", "Code", "Phase 5: builds web_sessions (marketing-site browsing; known customers + anonymous ghosts, engagement_tier-driven volume)"),
    ("generator/validate_web_sessions.py", "Code", "Phase 5: 5-layer validation for web_sessions"),
    ("data/web_sessions.csv", "Shipped table", "Phase 5: web_sessions table (30,285 rows: 6,476 identity-resolved + 23,809 anonymous)"),
    ("generator/build_web_events.py", "Code", "Phase 5: builds web_events (page_view/product_view/add_to_cart/begin_checkout/purchase/search; every order gets exactly one purchase event)"),
    ("generator/validate_web_events.py", "Code", "Phase 5: 5-layer validation for web_events"),
    ("data/web_events.csv", "Shipped table", "Phase 5: web_events table (117,706 rows)"),
    ("generator/build_app_sessions.py", "Code", "Phase 5: builds app_sessions (in-app fitness usage, driven by real subscription intervals + course orders, keyed off engagement_tier)"),
    ("generator/validate_app_sessions.py", "Code", "Phase 5: 5-layer validation for app_sessions"),
    ("data/app_sessions.csv", "Shipped table", "Phase 5: app_sessions table (19,610 rows across 496 customers)"),
    ("generator/build_app_events.py", "Code", "Phase 5: builds app_events (class_started/workout_completed/workout_abandoned/streak_achieved -- streaks derived from real consecutive session dates) -- completes Phase 5"),
    ("generator/validate_app_events.py", "Code", "Phase 5: 5-layer validation for app_events"),
    ("data/app_events.csv", "Shipped table", "Phase 5: app_events table (39,370 rows) -- completes Phase 5"),
    ("generator/build_braze_email_campaigns.py", "Code", "Phase 6: builds braze_email_campaigns (hand-curated: 7 triggered + 2 broadcast) -- built first, events table needs it"),
    ("generator/validate_braze_email_campaigns.py", "Code", "Phase 6: 5-layer validation for braze_email_campaigns"),
    ("data/braze_email_campaigns.csv", "Shipped table", "Phase 6: braze_email_campaigns table (9 rows)"),
    ("generator/build_web_events.py", "Code", "Phase 5: builds web_events (retroactive fix: timestamp offsets now rounded to whole seconds, fixing a latent fractional-second formatting bug across all 117,706 rows)"),
    ("data/web_events.csv", "Shipped table", "Phase 5: web_events table (117,706 rows; retroactively rebuilt for the whole-second timestamp fix, same counts/logic)"),
    ("generator/build_braze_email_events.py", "Code", "Phase 6: builds braze_email_events (Send/Open/Click/Bounce/Unsubscribe funnel, derived from real trial/payment-failure/order/cart/reactivation sources)"),
    ("generator/validate_braze_email_events.py", "Code", "Phase 6: 5-layer validation for braze_email_events"),
    ("data/braze_email_events.csv", "Shipped table", "Phase 6: braze_email_events table (26,328 rows, 18,187 sends)"),
    ("generator/build_braze_push_campaigns.py", "Code", "Phase 6: builds braze_push_campaigns (hand-curated: 5 triggered + 2 broadcast, push-appropriate subset) -- built before events table needs it"),
    ("generator/validate_braze_push_campaigns.py", "Code", "Phase 6: 5-layer validation for braze_push_campaigns"),
    ("data/braze_push_campaigns.csv", "Shipped table", "Phase 6: braze_push_campaigns table (7 rows)"),
    ("generator/build_braze_push_events.py", "Code", "Phase 6: builds braze_push_events (Send/Open/Click/Bounce/Unsubscribe funnel, gated on push_opt_in as a hard delivery precondition) -- completes Phase 6 (all 4 tables)"),
    ("generator/validate_braze_push_events.py", "Code", "Phase 6: 5-layer validation for braze_push_events"),
    ("data/braze_push_events.csv", "Shipped table", "Phase 6: braze_push_events table (9,897 rows, 7,851 sends) -- completes Phase 6 (25 of 47 tables shipped; Phase 7 paid media remains)"),
    ("generator/paid_media_common.py", "Code", "Phase 7: shared helpers used by all 6 platforms' daily performance tables -- maps any date to the seasonality calendar/channel-mix week and draws each day's per-channel spend baseline"),
    ("generator/build_meta_campaigns.py", "Code", "Phase 7 (Meta 1/4): builds meta_campaigns (4 evergreen objective campaigns + 3 flighted brand_lift campaigns timed near BFCM)"),
    ("generator/validate_meta_campaigns.py", "Code", "Phase 7: 5-layer validation for meta_campaigns"),
    ("data/meta_campaigns.csv", "Shipped table", "Phase 7 (Meta 1/4): meta_campaigns table (7 rows)"),
    ("generator/build_meta_ads.py", "Code", "Phase 7 (Meta 2/4): builds meta_ads (functions as the ad-set-level entity -- targeting_segment_id for retargeting/lookalike only)"),
    ("generator/validate_meta_ads.py", "Code", "Phase 7: 5-layer validation for meta_ads"),
    ("data/meta_ads.csv", "Shipped table", "Phase 7 (Meta 2/4): meta_ads table (10 rows)"),
    ("generator/build_meta_ad_insights_daily.py", "Code", "Phase 7 (Meta 3/4): builds meta_ad_insights_daily (spend/impressions/clicks driven by the shared seasonality calendar + channel-mix schedule)"),
    ("generator/validate_meta_ad_insights_daily.py", "Code", "Phase 7: 5-layer validation for meta_ad_insights_daily, incl. weekly-spend-vs-web_sessions correlation check"),
    ("data/meta_ad_insights_daily.csv", "Shipped table", "Phase 7 (Meta 3/4): meta_ad_insights_daily table (7,396 rows)"),
    ("generator/build_meta_ad_actions_daily.py", "Code", "Phase 7 (Meta 4/4): builds meta_ad_actions_daily (normalized actions array, derived directly from meta_ad_insights_daily.csv's own clicks) -- completes Meta (1 of 6 platforms)"),
    ("generator/validate_meta_ad_actions_daily.py", "Code", "Phase 7: 5-layer validation for meta_ad_actions_daily"),
    ("data/meta_ad_actions_daily.csv", "Shipped table", "Phase 7 (Meta 4/4): meta_ad_actions_daily table (35,504 rows) -- completes Meta"),
    ("generator/build_google_search_campaigns.py", "Code", "Phase 7 (Google Search 1/4): builds google_search_campaigns (5 evergreen objective campaigns, incl. an always-on brand-term defense campaign)"),
    ("generator/validate_google_search_campaigns.py", "Code", "Phase 7: 5-layer validation for google_search_campaigns"),
    ("data/google_search_campaigns.csv", "Shipped table", "Phase 7 (Google Search 1/4): google_search_campaigns table (5 rows)"),
    ("generator/build_google_search_ad_groups.py", "Code", "Phase 7 (Google Search 2/4): builds google_search_ad_groups (targeting_segment_id for RLSA retargeting/similar-audience lookalike only)"),
    ("generator/validate_google_search_ad_groups.py", "Code", "Phase 7: 5-layer validation for google_search_ad_groups"),
    ("data/google_search_ad_groups.csv", "Shipped table", "Phase 7 (Google Search 2/4): google_search_ad_groups table (8 rows)"),
    ("generator/build_google_search_keyword_performance_daily.py", "Code", "Phase 7 (Google Search 4/4 by build order): builds google_search_keyword_performance_daily -- the granular ground truth google_search_performance_daily aggregates from"),
    ("generator/validate_google_search_keyword_performance_daily.py", "Code", "Phase 7: 5-layer validation for google_search_keyword_performance_daily, incl. weekly-spend-vs-web_sessions correlation check"),
    ("data/google_search_keyword_performance_daily.csv", "Shipped table", "Phase 7 (Google Search 4/4 by build order): google_search_keyword_performance_daily table (19,932 rows)"),
    ("generator/build_google_search_performance_daily.py", "Code", "Phase 7 (Google Search 3/4 by schema order): builds google_search_performance_daily, aggregated exactly from keyword_performance_daily.csv up to ad_group/day grain -- completes Google Search (2 of 6 platforms)"),
    ("generator/validate_google_search_performance_daily.py", "Code", "Phase 7: 5-layer validation for google_search_performance_daily, incl. exact-sum reconciliation against keyword_performance_daily.csv"),
    ("data/google_search_performance_daily.csv", "Shipped table", "Phase 7 (Google Search 3/4 by schema order): google_search_performance_daily table (8,751 rows) -- completes Google Search"),
    ("generator/build_youtube_campaigns.py", "Code", "Phase 7 (YouTube 1/3): builds youtube_campaigns (4 evergreen objective campaigns + 3 flighted brand_lift campaigns, mirroring Meta's structure since YouTube Brand Lift is a real flighted measurement product)"),
    ("generator/validate_youtube_campaigns.py", "Code", "Phase 7: 5-layer validation for youtube_campaigns"),
    ("data/youtube_campaigns.csv", "Shipped table", "Phase 7 (YouTube 1/3): youtube_campaigns table (7 rows)"),
    ("generator/build_youtube_ad_groups.py", "Code", "Phase 7 (YouTube 2/3): builds youtube_ad_groups (targeting_segment_id for retargeting/lookalike only)"),
    ("generator/validate_youtube_ad_groups.py", "Code", "Phase 7: 5-layer validation for youtube_ad_groups"),
    ("data/youtube_ad_groups.csv", "Shipped table", "Phase 7 (YouTube 2/3): youtube_ad_groups table (9 rows)"),
    ("generator/build_youtube_performance_daily.py", "Code", "Phase 7 (YouTube 3/3): builds youtube_performance_daily (video_views/video_view_rate/average_cpv, spend-driven by the shared seasonality calendar + channel-mix schedule) -- completes YouTube (3 of 6 platforms)"),
    ("generator/validate_youtube_performance_daily.py", "Code", "Phase 7: 5-layer validation for youtube_performance_daily, incl. weekly-spend-vs-web_sessions correlation check"),
    ("data/youtube_performance_daily.csv", "Shipped table", "Phase 7 (YouTube 3/3): youtube_performance_daily table (6,394 rows) -- completes YouTube"),
]


def last_modified_pacific(rel_path):
    import subprocess
    if rel_path == "File_Manifest.xlsx":
        # Self-referential: this file is about to be overwritten, so use "now"
        # rather than its stale pre-save mtime.
        result = subprocess.run(
            ["date", "+%Y-%m-%d %H:%M %Z"],
            env={**os.environ, "TZ": "America/Los_Angeles"},
            capture_output=True, text=True,
        )
        return result.stdout.strip()
    full_path = os.path.join(PROJECT_ROOT, rel_path)
    ts = os.path.getmtime(full_path)
    result = subprocess.run(
        ["date", "-d", f"@{int(ts)}", "+%Y-%m-%d %H:%M %Z"],
        env={**os.environ, "TZ": "America/Los_Angeles"},
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "File Manifest"

    headers = ["File Path", "Category", "Description", "Last Updated (Pacific)"]
    ws.append(headers)
    for col, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2A6F6F")
        cell.alignment = Alignment(vertical="center")

    for rel_path, category, description in FILES:
        timestamp = last_modified_pacific(rel_path)
        ws.append([rel_path, category, description, timestamp])

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")
            cell.alignment = Alignment(vertical="center", wrap_text=(cell.column == 3))

    widths = {1: 48, 2: 16, 3: 60, 4: 22}
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.freeze_panes = "A2"
    wb.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH} with {len(FILES)} file rows")


if __name__ == "__main__":
    build()
