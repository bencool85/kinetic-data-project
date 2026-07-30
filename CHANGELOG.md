# Changelog

All notable decisions and file changes for this project, in plain English.

## 2026-07-30 — Project kickoff & planning

- Aligned on the business concept: **Kinetic**, an on-demand fitness content platform
  (app + web) selling subscriptions (Basic/Plus), a la carte training courses, and
  branded merch/gear. No proprietary hardware (unlike Peloton).
- Decided to build fully synthetic data rather than use public real-world datasets,
  because (a) ad-platform-shaped raw data has no public equivalent, and (b) a known
  simulation ground truth lets us later verify whether AI agents built on top of this
  data give *correct* answers.
- Locked scope: **100 customers**, 3 years of history (Aug 2023 – Jul 2026), raw
  source-system-shaped tables (no pre-built dim/fact mart), delivered as CSVs, with
  intentional realistic messiness.
- Finalized the **47-table schema** across Identity/Account, Product Catalog, Commerce,
  Subscriptions, Audience & Segmentation, six paid-media platforms (Meta, Google Search,
  YouTube, DV360, Snap, TikTok), Braze Email & Push, Web Browsing, and App Usage. See
  `docs/schema_reference.md`.
- Pressure-tested the schema against ~18 target canonical metrics (MRR, churn, LTV,
  CAC/ROAS by channel, course attach rate, engagement, etc.) — all derivable, subject to
  five conventions locked into Phase 0 (see `docs/generation_plan.md`).
- Decided on a **shared master-timeline generation approach**: one ground-truth
  simulation per customer built first (Phase 0, internal only), with every one of the
  47 tables derived from it — preventing impossible cross-table scenarios by
  construction rather than catching them after the fact. Validation runs after every
  single table, cumulatively.
- Set up this project folder (synced to `/Claude/Data_Engineering_Project_July2026` in
  Ben's iCloud Drive) with a git-backed history in the Claude cloud workspace.

**Next up:** Phase 0 — build the master timeline generator, anonymous population, and
seasonality calendar.

## 2026-07-30 — Phase 0, Steps 1-3: parameters, seasonality calendar, channel mix

- `generator/params.py` — all global constants (100 customers, 2,000 anonymous ghosts,
  Aug 2023-Jul 2026 date range, trial/pricing/rate assumptions).
- `generator/build_calendar.py` — builds the weekly seasonality multiplier and the
  channel-mix-over-time schedule.
- Output: `internal/_sim_seasonality_calendar.csv`, `internal/_sim_channel_mix_schedule.csv`,
  `internal/seasonality_preview.png` (visual sanity check).
- Realized shape: yearly avg multiplier grows 1.15 (2023) -> 2.31 (2026); monthly shape
  peaks in January (2.93) and November (2.12), dips in summer (Jun-Aug ~1.1-1.5) as
  intended. Channel mix drifts Meta 28%->20%, TikTok 10%->25%, Snap 8%->5% over the
  3 years.
- Awaiting review before proceeding to Steps 4-6 (anonymous population + per-customer
  master timelines).

## 2026-07-30 — Process fix: file manifest + every-file sync

- Caught a gap: the Steps 1-3 files were built and sent into the conversation, but not
  actually pushed to Ben's synced folder until he flagged it.
- Added `File_Manifest.xlsx` (project root) — one row per file committed to the folder,
  with a category, description, and last-updated timestamp (Pacific time, pulled from
  the file's real modification time). Rebuilt via `generator/build_manifest.py`.
- **New standing process going forward:** every file created or edited on my side gets
  (1) written locally, (2) added/updated as a row in `File_Manifest.xlsx`, (3) sent and
  committed to the synced Mac folder, (4) committed to git — every time, no exceptions.
- Added `.gitignore` for Python `__pycache__`.

## 2026-07-30 — Phase 0, Steps 4-8: anonymous population + customer master timelines

- `generator/build_anonymous_population.py` — generated ~2,000 anonymous "ghost"
  visitors (7.3% convert to a guest merch purchase, matching the ~8% target).
- `generator/simulate_customers.py` — the core Phase 0 simulation: for each of the
  100 customers, simulates signup, trial, subscription intervals (with churn and
  win-back), order events, and engagement tier as one ground-truth timeline.
- Output: `internal/_sim_anonymous_population.csv`, `internal/_sim_customer_timeline.json`
  (full nested ground truth), `internal/_sim_customer_timeline_summary.csv` (flattened),
  `internal/_sim_attribution_ground_truth.json` (true acquisition/reactivation channel).
- Self-check results: 58/100 ever subscribed (target 60), trial conversion realized
  70.7% (target 65%, within normal variance), signups tracked the growth curve
  (11/33/35/21 by year), churn split 24 voluntary/11 involuntary (~69/31 vs 75/25
  target). 266 customer orders (114 course, 152 merch) + 146 guest orders.
- **Flagged for review:** only 22.4% (13/58) of ever-subscribed customers are still
  active today — a consequence of ~11-month mean tenure + only 25% win-back rate.
  Awaiting Ben's call on whether to keep this churn severity or loosen it.
- Initially missed syncing this batch to Ben's folder until asked — fixed; this is
  now happening as part of the same step, not a follow-up.

## 2026-07-30 — Retention model recalibrated: 100 active subscribers, churnier retention

- Target changed from "100 total customers" to "100 *active* subscribers today,"
  with an approved funnel: ~1,100 total customers LTD, 658 trial starters, 205
  ever-paid, 102 active / 103 lapsed (11 still buying since lapsing, 92 quiet).
- Trial-to-paid conversion rate lowered from 65% to 30% (judged too high).
- Lapsed-still-buying rate lowered from 30% to 10%.
- New churn model: a single constant churn rate can't hit both "40% annual
  retention" and "3-month average churner tenure" at once (mechanically the same
  number under a constant hazard). Replaced with a two-segment model —
  `LOYAL_SEGMENT_SHARE` (38.9%, essentially never organically churns) and
  `QUICK_CHURN_MEAN_TENURE_MONTHS` (3.0, the rest) — landing both targets
  simultaneously since nearly all realized churns come from the quick segment.
- `generator/simulate_customers.py` rewritten: two-segment subscription lifecycle,
  explicit post-lapse purchase gating (`LAPSED_STILL_BUYING_RATE`), `churn_segment`
  now recorded per customer.
- Scaled `N_CUSTOMERS` 100 -> 1,100 and `N_ANONYMOUS` 2,000 -> 21,800 (proportional)
  to sustain 100 active subscribers under the new, churnier retention curve.
- Added `generator/build_simulation_charts.py` (funnel + segment-breakdown charts,
  colors from the dataviz skill's validated reference palette) and
  `docs/phase0_simulation_analysis.md` (full written analysis of the results).
- Realized vs. target: trial conversion 31.2% (target 30%), churn segment split
  59/41 quick/loyal (target 61/39), avg churner tenure 2.68mo (target 3.0),
  lapsed-still-buying 10.7% (target 10%), active subscribers 102 (target 100) —
  all within normal sampling variance.

## 2026-07-30 — January-clustered win-backs + email-acquired subscribers

- **Win-back timing is now January-clustered.** Reactivations are sampled by
  calendar month only (same relative weights as `MONTHLY_SEASONALITY`), with a
  minimum 1-month gap enforced after churn, so total subscribers peak every
  January and taper through the year, matching new-signup seasonality.
  Added `sim_utils.sample_seasonal_month_date()` for this. First attempt reused
  the full seasonality-calendar sampler (which also bakes in the 3-year growth
  trend) and produced a spurious mid-year spike instead of a January one, since
  growth + end-of-window truncation dominated the weighting; fixed by weighting
  strictly on calendar month, independent of year or growth trend. Verified the
  fixed sampler against a 20,000-draw isolated test (Jan ≈13.7% vs. target
  ≈14.2%, Jul ≈5.8% vs. target ≈5.9%) since the actual simulation only produces
  ~25 reactivation events, too few to visually confirm the skew on its own.
- **New acquisition pathway:** course/merch-only customers (never subscribed) can
  now be nudged into a trial by a targeted "come try a membership" email, timed
  3-12 months after their first course/merch order (relative to their own
  purchase history, not the seasonal calendar). New params:
  `MERCH_TO_SUB_EMAIL_RATE` (17.5%, target range 15-20%) and
  `MERCH_TO_SUB_TRIAL_CONVERSION_RATE` (47.5%, target range 45-50%, reflecting
  better odds for this warm, already-purchasing audience vs. the 30% baseline).
  Their `account_type` stays `course_merch_only` (their original signup reason)
  even if they convert — subscription status must be read from
  `trial`/`subscription_intervals`/`churn_date`, not `account_type`. The `trial`
  object now carries a `trigger` field (`"signup"` or `"email_reactivation"`) as
  the attribution answer key for Phase 6.
- **Bug fix (engagement tier):** tier assignment was keyed off original
  `account_type` rather than actual conversion/active status, so a subscriber
  whose trial never converted could still be tiered "power." Fixed to key off
  whether the customer ever converted and is currently active/lapsed — this
  also correctly tiers the new email-acquired subscribers.
- **Bug fix (edge-case impossible state):** a customer signing up in the final
  week of the dataset window could have their 7-day trial resolve past
  `END_DATE` and get marked "converted" with zero subscription intervals — an
  impossible state for the eventual `subscriptions` table. Fixed: such trials
  now get outcome `trial_in_progress` instead (3 occurrences in this run).
- Adding an active-subscriber-producing channel pushed active subscribers to
  128 (vs. the 100 target) on the first run at the existing 1,100-customer
  scale, so `N_CUSTOMERS` and `N_ANONYMOUS` were re-derived down (1,100→860,
  21,800→17,050) to land back near target — same empirical-correction approach
  used in the original retention calibration. Landed at 98 active subscribers.
- Regenerated `internal/_sim_customer_timeline.json` and related artifacts,
  `internal/funnel_chart.png`, `internal/segment_breakdown_chart.png`, and
  rewrote `docs/phase0_simulation_analysis.md` to cover both new mechanics and
  the corrected numbers. Added a short section to `docs/generation_plan.md`'s
  master timeline spec describing the two acquisition pathways and the
  `trial.trigger` field.

## 2026-07-30 — Phase 1 kickoff: aligned scope, built `products` (table 1 of 47)

- Aligned on Phase 1 specifics before building: a minimal ~12-item product
  catalog (one flagship product per existing price tier), a Plus Annual
  subscription plan added ($314.00, matching Basic's ~25.4% annual discount
  ratio), a small 10-segment definition list (7 customer-grain, 3
  anonymous-grain), and device records for the anonymous ghost population too
  (not just the 860 known customers).
- Built `generator/build_products.py` -> `data/products.csv`: 5 course products
  (one per COURSE_PRICE_TIERS value) + 7 merch products (one per
  MERCH_PRICE_TIERS value, plus a second item at the $24.99 tier).
  `is_subscription_eligible` is True only for courses (an active subscription
  includes course-catalog access, which is exactly why the simulation never
  places a course order during an active subscription window); merch is never
  subscription-eligible, only ever discounted.
- Built `generator/validate_products.py` — 18 checks across the same 5 layers
  used throughout this project (structural / referential / temporal /
  business-rule / distributional). Note: DuckDB isn't installable in this
  sandbox (no network access to fetch new packages, confirmed by testing a
  few other new installs), so validation is implemented directly in pandas
  instead of SQL-over-DuckDB -- same rigor, different tool. Will apply to
  every later table's validator too.
- Key correctness check: every price that appears in the Phase 0 simulation's
  order_events (and the anonymous population's guest purchases) must resolve
  to a real product here. This required accounting for the subscriber merch
  discount explicitly -- a discounted merch order's price (e.g. $19.99) is a
  *different number* than its catalog base_price ($24.99), so the check
  verifies against both the full and discounted price, while guest purchases
  (never subscribed, never discounted) are checked against full price only.
  All 18 checks passed on the first run.
- Added `PLUS_ANNUAL = 314.00` to `params.py` (~25.4% off monthly-equivalent,
  the same discount ratio as `BASIC_ANNUAL`).
- Built `generator/build_product_variants.py` -> `data/product_variants.csv`
  (21 variants across 12 products): courses get a single "Standard Access"
  variant (digital, no sizing); the tee/shorts/pullover get S/M/L/XL; the cap
  gets "One Size" instead of the originally-sketched blanket S/M/L/XL for all
  apparel (a small realism refinement -- caps aren't usually sized S-XL like
  other apparel); everything else gets one "Default" variant. No per-variant
  price adjustment -- the product's base_price already sets the price.
- Built `generator/validate_product_variants.py` — 18 checks, same 5 layers.
  This is the first table with a real foreign key to another shipped table
  (`product_id` -> `products.product_id`), so referential integrity does real
  work for the first time: checked both directions (every variant resolves to
  a real product, and every product has at least one sellable variant so
  nothing in the catalog is orphaned). All 18 checks passed on the first run.
- Built `generator/build_subscription_plans.py` -> `data/subscription_plans.csv`
  (4 rows: Basic/Plus x monthly/annual, Stripe-shaped: tier, billing_interval,
  price, currency).
- Built `generator/validate_subscription_plans.py` — 19 checks. Flagged an
  open gap for later phases: the Phase 0 master timeline only tracks plan
  *tier* per subscription interval ("basic"/"plus"), not billing_interval
  (monthly vs. annual) -- that split doesn't exist in the ground truth yet, so
  Phase 2 (`subscriptions`) will need to assign monthly-vs-annual itself when
  it builds real interval rows. Business-rule checks confirmed both annual
  plans are genuinely discounted vs. paying monthly (not just relabeled), and
  that Plus's annual discount ratio (25.2%) is consistent with Basic's
  (25.4%) rather than an arbitrary number. All 19 checks passed.
- Added `EMAIL_OPT_IN_RATE` (88%), `PUSH_OPT_IN_RATE` (45%), and
  `IS_DELETED_RATE` (2%) to `params.py`.
- Built `generator/build_customers.py` -> `data/customers.csv` (860 rows) —
  the first table derived directly from the master timeline. Defines the
  `customer_id_for()` mapping (timeline integer id N -> shipped `cust_{N:05d}`)
  that every later table referencing a customer will import, so the mapping
  can't drift between tables. Synthetic name/email generation (no `faker`
  available -- confirmed no new pip packages can be installed in this
  sandbox), with collision-safe unique emails. Soft-deleted accounts (~2%)
  get PII scrubbed (placeholder name, `deleted_user_NNNNN@deleted.kinetic.invalid`
  email, both opt-ins forced False) while `customer_id` and all historical
  rows in other tables stay intact -- a realistic "messy data" touch matching
  the project's original intentional-messiness scope.
- Built `generator/validate_customers.py` — 22 checks. Because this table
  comes straight from the timeline, the key validation is a direct 1:1
  reconciliation: same row count (860 vs. 860), every timeline customer_id
  maps to exactly one row, and `created_at`'s date + `signup_source` match the
  timeline's `signup_date`/`signup_source` exactly for all 860 customers (0
  mismatches) -- not sampled, checked for every row. All 22 checks passed.
