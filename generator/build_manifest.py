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
    ("generator/build_anonymous_population.py", "Code", "Phase 0 Step 4: builds the ~2,000-person anonymous ghost population"),
    ("generator/simulate_customers.py", "Code", "Phase 0 Steps 5-6: per-customer master timeline + attribution ground truth"),
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
    ("generator/build_devices.py", "Code", "Phase 1: builds devices (customer + anonymous-ghost devices)"),
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
