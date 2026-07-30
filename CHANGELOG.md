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

## 2026-07-30 — Bug fix: opt-in flags didn't account for email/push touchpoints

- Ben caught a real gap in `customers`: `email_opt_in`/`push_opt_in` were
  rolled independently of the timeline, with no guarantee that a customer
  who was actually reactivated (or, for email, converted via the
  merch-to-subscriber trigger) via that channel was also opted into it --
  logically, you can't receive a marketing email/push you never opted into.
  Checked the shipped data directly: 9 of 860 customers were touched by email
  (reactivated or converted via email) but had `email_opt_in=False` -- a real
  violation. Push had zero violations this run, but only by chance (0 of the
  25 reactivations happened to land on the push channel this seed) -- the
  underlying bug applied equally to both.
- Fixed in `generator/build_customers.py`: a customer's reactivation history
  (and, for email, the merch-to-subscriber trigger) is now checked *before*
  rolling opt-in -- anyone touched by a channel gets that opt-in forced True,
  rather than left to chance. Soft-deleted accounts still force both opt-ins
  False regardless of history (deletion legitimately overrides a customer's
  past opt-in state, since they could have opted in, received the email
  years ago, then since deleted their account).
- Added 2 permanent checks to `generator/validate_customers.py` so this can't
  silently regress: every non-deleted customer touched by an email
  touchpoint has `email_opt_in=True` (49 customers touched, 0 violations),
  and the same for push (0 touched this run, 0 violations). Re-ran the full
  22+2=24-check suite; all pass.
- Note: fixing this reshuffled the shared RNG stream for unrelated fields
  (names, is_deleted draws) for customers after the first email-touched one
  in generation order -- an accepted, known consequence of using one
  sequential RNG per customer (documented earlier in this project); the data
  is still fully reproducible from the seed, just different-looking row by
  row than the prior (buggy) version.

## 2026-07-30 — Emails made unambiguously fake

- Ben asked that no generated email address could be mistaken for a real
  person's real email. Prefixed every domain with "fake" (gmail.com ->
  fakegmail.com, yahoo.com -> fakeyahoo.com, etc. across all 8 domains) --
  still reads as "gmail-shaped" for realism, but can never collide with (or
  be confused for) an actual address.
- Added a permanent structural check to `validate_customers.py`: every email
  domain must start with `fake` or be the deleted-account placeholder
  (`deleted.kinetic.invalid`) -- never a real-looking domain. 25/25 checks
  pass.

## 2026-07-30 — Phase 1: `customer_addresses` (table 5 of 47)

- Who gets an address: **billing** for every subscriber-path customer (a
  trial requires a card up front, even if they never converted) or anyone
  with at least one order; **shipping** additionally for anyone with a merch
  order (courses are digital, nothing to ship). Soft-deleted customers get
  **zero** address rows -- full erasure, stricter than the name/email scrub
  in `customers`, since address has no downstream revenue-table dependency
  the way order/subscription history does.
- Addresses made obviously fake the same way emails were: every street
  address is guaranteed non-existent by construction --
  "<number> Fake <word> <suffix>" (e.g. "5075 Fake Canyon Road"). No real
  street is named "Fake ___", so the full address can never resolve to an
  actual deliverable location. City/state/zip are drawn from 25 real U.S.
  metros for plausible geographic variety in later analytics -- safe to keep
  realistic since a city/state/zip alone identifies no one; only the
  guaranteed-fake street makes the full address non-deliverable.
- 30% of customers needing shipping get a *different* address than their
  billing address (gift shipping, work address, etc. -- realistic messiness);
  70% ship to the same address as billing.
- Built `generator/validate_customer_addresses.py` — 21 checks. Notably:
  exact set-equality checks confirming *precisely* the right customers have a
  billing address and *precisely* the right customers have a shipping
  address (no missing, no extra), zero address rows for deleted customers,
  shipping `created_at` matches the customer's first merch-order date exactly
  for all 582 shipping rows, and every street address contains the literal
  word "Fake". All 21 checks passed on the first run.

## 2026-07-30 — Phase 1: `devices` (table 6 of 47) + a real Phase 0 bug found via validation

- Built `generator/build_devices.py` -> `data/devices.csv` (18,042 rows): a
  primary device per non-deleted customer carrying their exact
  `pre_signup_anonymous_id` from the timeline (~20% also get a 2nd device),
  plus one device per anonymous ghost (17,050, `customer_id` null),
  per Ben's earlier decision that the ghost population should get device
  records too. Deleted customers get zero devices (same full-erasure pattern
  as `customer_addresses`).
- **Validation caught two real correctness bugs, both fixed at the source:**
  1. 47 of 17,050 anonymous ghosts had `first_seen_date` up to 3 days *past*
     `END_DATE` -- an impossible state (first seen after the dataset's own
     observation window ends). Root cause: `build_anonymous_population.py`
     (Phase 0) called `sample_weighted_date()` without `start_date`/`end_date`
     bounds, so the calendar's last week (`week_start` a few days before
     `END_DATE`) plus a random 0-6-day offset could overshoot. Fixed by
     passing explicit bounds, matching how every other date-sampling call
     in this project already does it. **Regenerated
     `internal/_sim_anonymous_population.csv`** -- only the 47 affected rows
     changed (clamped to `END_DATE`); guest-purchase rate stayed at 7.4%,
     nothing else moved.
  2. 4 customer devices inherited a `last_seen_at` past `END_DATE` from the
     `trial_in_progress` edge case (a trial that hadn't resolved yet when the
     dataset window closed, added in an earlier fix) -- its recorded
     `trial.end` is legitimately up to `TRIAL_DAYS` past `END_DATE`. Fixed
     `_last_activity_date()` in `build_devices.py` to clip at `END_DATE`.
  Both were only surfaced because `validate_devices.py` checks
  `last_seen_at <= END_DATE` for every row -- exactly the kind of
  impossible-scenario check this project is built around.
- Built `generator/validate_devices.py` — 20 checks, including an exact
  reconciliation that every customer's primary device carries their precise
  `pre_signup_anonymous_id` (0 mismatches of 849), and that the ghost and
  customer anonymous_id namespaces never collide. All 20 checks passed after
  the two fixes above.

## 2026-07-30 — Phase 1: `identity_map` (table 7 of 47)

- Built `generator/build_identity_map.py` -> `data/identity_map.csv` (992
  rows) from `devices.csv` + `customers.csv` rather than the raw timeline,
  since devices.csv already carries the customer_id every known device
  resolved to. One row per customer-linked device: the primary device
  (carrying the customer's exact `pre_signup_anonymous_id`) resolves at
  `resolution_type="signup"`, timestamped to the customer's `created_at`
  exactly (not their earlier `first_seen_at` -- the anonymous_id has no
  customer_id link until the account exists); any 2nd device resolves at
  `resolution_type="login"`, timestamped to that device's `first_seen_at`.
  Soft-deleted customers have zero rows, automatically, since devices.csv
  already excludes them.
- Built `generator/validate_identity_map.py` — 17 checks, including exact
  parity between identity_map and devices (992 = 992, no orphans either
  direction), an exact match on every signup resolution's anonymous_id vs.
  the timeline's `pre_signup_anonymous_id` (0 mismatches of 849), and
  `resolved_at` never preceding the device's own `first_seen_at`. All 17
  checks passed.
- One Phase 1 table remains: `segments` (definitions only). Products,
  product_variants, subscription_plans, customers, customer_addresses,
  devices, and identity_map are done.

## 2026-07-30 — Phase 1 complete: `segments` (table 8 of 47)

- Built `generator/build_segments.py` -> `data/segments.csv` (10 rows,
  definitions only -- membership is Phase 4): 7 customer-grain segments
  (Active Subscriber, Lapsed 0-30/31-90/90+ Days, Course/Merch-Only-Never-
  Subscribed, Trial In Progress, High-LTV Customer) and 3 anonymous_device-
  grain ad-platform audiences (Website Visitors - Last 30 Days on
  google_search, Cart Abandoners on meta, Lookalike - Recent Converters on
  tiktok), per the agreed small-scope design.
- The Lookalike audience's `created_at` is deliberately later than the
  others: a lookalike/similar-audience algorithm needs a real seed audience
  of converters to model itself on, so it can't have existed since day 1.
  Computed directly from the simulation -- the 50th real conversion lands
  ~429 days after START_DATE -- and dated it ~2 weeks after that.
- Built `generator/validate_segments.py` — 14 checks, including a direct
  check that >=50 real conversions existed in the timeline by the Lookalike
  segment's `created_at` (50 did, exactly at the threshold by construction).
  All 14 checks passed.
- **This completes Phase 1** (8 of 8 tables: products, product_variants,
  subscription_plans, customers, customer_addresses, devices, identity_map,
  segments). Next up per `docs/generation_plan.md`: Phase 2 (subscriptions,
  subscription_events, invoices).

## 2026-07-30 — Bug fix: lapsed-but-still-buying customers didn't fit any segment

- Ben caught a real gap: "Lapsed 90+ Days (Quiet)" baked "no purchase
  activity since" directly into its definition, and the two shorter lapsed
  buckets were ambiguous about purchase behavior -- so a customer who
  lapsed their subscription but kept buying courses/merch (a real,
  explicitly-modeled population -- 6 of 76 lapsed subscribers per the Phase
  0 analysis) didn't cleanly belong to any of the 7 segments.
- Fixed by separating lifecycle stage from behavior: renamed "Lapsed 90+
  Days (Quiet)" back to a purely time-based "Lapsed 90+ Days" (dropped the
  purchase-activity condition, matching how the 0-30/31-90 buckets already
  worked), and added a new, separate customer-grain segment: **"Lapsed -
  Still Buying (Courses/Merch)"** -- a behavioral overlay that can co-occur
  with any of the three time buckets, rather than a 4th mutually-exclusive
  time bucket. This matches how real segmentation systems handle
  lifecycle-stage vs. behavior-tag segments (non-exclusive, overlapping).
  Customer-grain segments grew from 7 to 8 (11 total with the 3 anonymous
  ones) -- a deliberate, justified departure from the originally-agreed
  "~8-10" scope to fix a real coverage gap rather than silently leaving it.
- Added 2 new checks to `validate_segments.py`: confirmed the new segment
  isn't vacuous (6 real customers in the timeline actually match "lapsed AND
  has an order after their churn date"), and added a guard against ever
  re-introducing a purchase-activity condition into a lapsed time-bucket's
  description again. All 16 checks pass.

## 2026-07-30 — Added a "High Churn Risk" segment (renewal approaching + low engagement)

- Ben asked for a segment covering active subscribers with an upcoming
  renewal decision who aren't using their subscription much. Added
  **"High Churn Risk (Renewal Approaching, Low Engagement)"** as a 9th
  customer-grain segment (12 total with the 3 anonymous ones).
- This one is honestly flagged as only partially computable today, rather
  than pretending it's fully ready:
  - The "renewal approaching" half needs a computed next-renewal-date from
    `billing_interval`, which doesn't exist until Phase 2's `subscriptions`
    table (the same gap flagged back at `subscription_plans`).
  - The "low engagement" half is proxied today by `engagement_tier ==
    "regular"` -- discovered while building this that active subscribers in
    the simulation can only ever be tiered "power" or "regular," never
    "casual" (that tier is reserved for lapsed/never-subscribed customers),
    so there's currently no true "barely using it" tier among actives.
    "Regular" (the lower of the two) is the honest proxy until Phase 5's
    real app/web usage events give a proper recency/frequency signal.
  - Gave it its own `source_system` ("churn_propensity_model") distinct
    from the plain rule-based segments, since this one's conceptually a
    model output, not a SQL filter -- and dated its `created_at`
    (2024-10-25) to after the 20th real churn in the simulation exists (21
    had occurred by then), matching the same "needs real data to model
    against" logic used for the Lookalike audience.
- Added 4 new checks to `validate_segments.py`: the engagement-half proxy
  isn't vacuous (47 real active 'regular'-tier subscribers), the
  description explicitly names its Phase 2/5 dependency, it uses the
  distinct source_system, and its created_at postdates >=20 real churns.
  All 20 checks pass.
