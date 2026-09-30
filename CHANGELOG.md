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
- Ben decided: don't fix the engagement_tier proxy now -- instead, once
  Phase 5 (app/web usage tables) is built, low engagement must be shown
  directly in real, countable usage activity there, and whoever gets
  computed as low-usage in `customer_segment_membership` (Phase 4) must
  match. Recorded this as a locked commitment in
  `docs/generation_plan.md`'s new "Cross-phase consistency commitments"
  section, alongside the earlier-flagged billing_interval gap, so both
  are checked against when those phases actually get built rather than
  forgotten.

## 2026-07-30 — Replicated anonymous-grain segments across all 6 ad platforms

- Ben's comment: the anonymous-grain audiences shouldn't exist on just one
  platform each (e.g. Cart Abandoners only on Meta) -- every platform that
  can receive a retargeting pixel should get its own version. All 6
  paid-media platforms in this project's scope (meta, google_search,
  youtube, dv360, snap, tiktok) genuinely support pixel-based
  custom/retargeting audiences, so each of the 3 concepts (Website Visitors
  - Last 30 Days, Cart Abandoners, Lookalike - Recent Converters) now gets
  one row per platform instead of one row total.
- Anonymous-grain rows grew from 3 to 18 (3 concepts x 6 platforms). Total
  segments: 27 (9 customer-grain + 18 anonymous-grain), up from 12.
- `segment_name` disambiguated per platform to preserve uniqueness (e.g.
  "Cart Abandoners - Meta", "Cart Abandoners - Google Search", ... "Cart
  Abandoners - TikTok"). `created_at` kept identical across all 6
  platform-versions of a given concept -- no real reason the same
  underlying audience concept would be built on different platforms at
  meaningfully different times.
- Extended `_fake_platform_audience_id()` with realistic id shapes for the
  3 new platforms: YouTube (shares Google Ads infra, so numeric UserList-id
  shaped, in its own range so it never collides with Google Search's ids),
  DV360 (numeric, smaller id space), and Snap (UUID-shaped, since Snap's
  Marketing API keys audiences by UUID -- deterministic, not
  `uuid.uuid4()`, for reproducibility).
- Caught and fixed a real bug in the first pass at the Snap UUID generator:
  it zero-padded `i` on the left then sliced from the front of the padded
  string, which discarded the actual varying digits (at the end, since
  zfill pads left) for every small `i` -- collapsing seg_026's Snap id to
  the same near-all-zero UUID as several neighbors. Fixed by slicing the
  last 30 characters instead of the first 30, verified via the "unique
  platform_audience_id" check (previously failing, now passing with all
  27 ids unique).
- Updated `validate_segments.py`: the distributional check now expects 27
  total (9 customer, 18 anonymous, was 12/9/3); the Lookalike/converter-seed
  temporal check now matches by `segment_name.str.startswith(...)` instead
  of an exact name (since the plain "Lookalike - Recent Converters" name no
  longer exists on its own -- it's now 6 platform-suffixed rows) plus a new
  check confirming all 6 share the same `created_at`; added a new
  completeness check confirming each of the 3 concepts has exactly 6 rows,
  one per platform, with no platform missing or duplicated. 23/23 checks
  pass (up from 20, net of the 3 new checks above).
- Also corrected `File_Manifest.xlsx`'s segments descriptions, which had
  drifted stale (still said "10 definitions: 7 customer-grain, 3 anonymous"
  from an earlier count) -- now accurately reflects 27 rows / 9 customer /
  18 anonymous.

## 2026-07-30 — Phase 2 begins: built + validated `subscriptions` (1 of 3)

- Ben said proceed into Phase 2. First table: `subscriptions` -- Stripe-shaped
  billing objects, fully separate from storefront commerce (orders/payments
  come in Phase 3).
- Key design decision: one row per Stripe *subscription object*, not one row
  per customer or even one row per timeline interval. Specifically:
  - A customer's trial + its first interval (if the trial converts) are the
    SAME subscription object -- real Stripe subscriptions start `trialing`
    and move to `active` on conversion without getting a new ID. This also
    naturally covers trials that never convert (`canceled_during_trial`,
    `expired_passively`, still-unresolved `trial_in_progress`): each gets
    exactly one subscription object that just never leaves `trialing` or
    that lands straight in `canceled`.
  - Every later interval (a win-back reactivation after a full cancellation)
    is a genuinely NEW subscription object -- a real resubscribe, created
    straight into `active` with no trial.
  - 576 total subscription objects, reconciling EXACTLY against the
    timeline's own trial/interval structure (verified 1:1, not just
    approximately).
- **Resolved the long-flagged "billing_interval isn't in the master
  timeline" gap** (tracked in `generation_plan.md`'s Cross-phase consistency
  commitments since the `subscription_plans` table): neither billing_interval
  (monthly/annual) nor a plan tier for never-converted trials exist in Phase
  0 at all, so both are assigned here, once per subscription object, using
  this script's own seeded rng (~20% choose annual). `current_period_start`/
  `current_period_end` are computed by cycling forward from the object's
  start date -- for any open (active/past_due) subscription this guarantees
  `current_period_end` lands strictly after END_DATE, i.e. a real,
  still-future renewal date. That's exactly what the `segments` table's
  "High Churn Risk" segment has been waiting on since Phase 1 -- updated its
  description in `build_segments.py` to drop the now-resolved Phase 2
  dependency (only the Phase 5 engagement-proxy half is still open), and
  marked the commitment resolved in `generation_plan.md`. Re-ran
  `validate_segments.py` after that description edit -- still 23/23.
- Two more small mechanics layered on at this phase only (neither exists in
  the master timeline -- Phase 0 doesn't model billing-object-level detail):
  - `past_due`: a Stripe dunning/grace-period status for a small share of
    subscriptions that just renewed and are currently failing a payment
    retry but haven't been canceled yet. Landed exactly 1 subscription in
    this status this run -- combined with 97 `active`, that's 98 currently-
    open subscriptions, matching the long-established "98 active
    subscribers" figure from the Phase 0 analysis EXACTLY.
  - `paused` is a valid Stripe status (and listed in `schema_reference.md`'s
    enum) but is intentionally NOT modeled here -- 0 rows. Flagged explicitly
    in the table's docstring and checked by a validator assertion, rather
    than silently omitted.
- Caught and fixed a real distributional bug while validating: the
  `canceled_during_trial` outcome was initially tagged `cancel_reason =
  "voluntary"`, the same label used for real post-conversion voluntary
  churns. That diluted the INVOLUNTARY_CHURN_SHARE (25%) check against real
  churns -- actual came out to 13% because trial cancellations (which are
  always voluntary by definition, a much larger and mechanically unrelated
  population) were mixed in. Fixed by giving trial cancellations their own
  distinct reason, `trial_canceled`, separate from real `voluntary`/
  `involuntary` churns. Involuntary share came back to 23.8%, within the
  expected band.
- Added two new params to `params.py`: `ANNUAL_BILLING_SHARE` (0.20) and
  `PAST_DUE_RATE`/`PAST_DUE_WINDOW_DAYS` (0.06 / 14 days).
- `validate_subscriptions.py`: 27 checks across all 5 layers, including an
  exact row-count reconciliation against the timeline (576 = 576), an exact
  match on currently-open-subscription count against the timeline's own
  count of open intervals (98 = 98), and a check that re-derives the same
  subscription objects in-memory (importing `build_subscription_objects()`
  directly, rather than joining on a fragile CSV heuristic) to confirm every
  converted subscription's plan_id tier matches the timeline's own interval
  tier exactly (0 mismatches out of 576). All 27 checks pass.

## 2026-07-30 — Added `past_due_since` to subscriptions (amendment)

- While designing `subscription_events`, realized the past_due overlay
  (added in the previous entry) never actually recorded WHEN the failed
  renewal payment happened -- just flipped `status` to `past_due` with no
  supporting date. Added `past_due_since` to `subscriptions.csv` (nullable,
  populated only for `past_due` rows) so `subscription_events` has a single
  source of truth for the matching unresolved `payment_failed` event,
  instead of each table inventing its own date and risking drift.
- Additive, non-breaking change -- re-ran `validate_subscriptions.py` with
  one new check (`past_due_since` populated iff status='past_due', and
  falls between current_period_start and END_DATE). 28/28 checks pass (up
  from 27), same 576 rows, byte-identical otherwise (same seed).

## 2026-07-30 — Phase 2 continues: built + validated `subscription_events` (2 of 3)

- The event log behind every `subscriptions.csv` row. event_type vocabulary
  matches `schema_reference.md` exactly: trial_started, trial_converted,
  trial_expired, canceled_during_trial, renewed, upgraded, downgraded,
  payment_failed, canceled, resumed.
- Built by importing `build_subscription_objects()` directly from
  `build_subscriptions.py` (the same in-memory objects, not a re-parse of
  the CSV) -- single source of truth, so the two tables can't drift apart on
  subscription_id/customer_id/dates.
- Two kinds of source events:
  1. Directly derivable from each subscription object's own fields, no new
     invention: trial_started, trial_converted, trial_expired,
     canceled_during_trial, and the past_due overlay's own payment_failed
     (using the exact `past_due_since` date added in the amendment above).
  2. Pulled straight from the master timeline's raw `subscription_events`
     list (payment_failed blips + the unresolved one at involuntary churn,
     upgraded/downgraded, canceled, resumed) -- matched to the right
     subscription_id via (sim_customer_id, interval_id). old_plan/new_plan
     for upgraded/downgraded aren't stored on the raw event, but are fully
     implied by event_type in this design (upgraded is always
     basic->plus, downgraded always plus->basic, since the simulation only
     ever does one binary tier swap per interval) -- filled in here.
  `renewed` events don't exist anywhere in the timeline at all -- generated
  by cycling the same billing-interval math `subscriptions.py` already uses,
  from each object's origin date up to its current_period_start.
- **Added the "duplicate webhook-style events" messiness explicitly
  promised in `schema_reference.md`'s own intro** (previously unaddressed):
  a new `DUPLICATE_WEBHOOK_RATE` param (0.03) controls a share of events
  that get a byte-for-byte duplicate row -- same subscription/type/
  timestamp, only `event_id` differs -- simulating Stripe's at-least-once
  webhook delivery. Landed at 2.93%, within tolerance.
- 2,424 total events. Caught and fixed a real bug while validating: the
  intra-day time-of-day offset was originally assigned AFTER duplicating
  rows, keyed off each row's own `event_id` -- since the duplicate gets a
  different `event_id` than its original, this gave the "duplicate" a
  DIFFERENT timestamp than the event it was supposed to be a byte-for-byte
  copy of, defeating the whole point. Fixed by assigning the time-of-day
  offset BEFORE duplication (keyed on row position instead), so a
  duplicated row now carries the exact same full timestamp as its original.
- `validate_subscription_events.py`: 22 checks across all 5 layers,
  including exact-date cross-checks against `subscriptions.csv` for every
  directly-derivable event type (trial_started/converted/expired,
  canceled_during_trial, real canceled, the past_due payment_failed), an
  independently-recomputed `renewed`-event-count check (0 mismatches across
  576 subscription objects), and a duplicate-detection check that uses a
  natural key (subscription_id + event_type + event_at) rather than
  `event_id`, since real duplicate detection in a webhook pipeline can't
  rely on the receiver assigning the same ingestion id twice. All 22 pass.

## 2026-07-30 — Phase 2 complete: built + validated `invoices` (3 of 3)

- Last table in Phase 2. One row per Stripe invoice: the initial charge at
  trial-conversion/resubscribe, one per successful renewal, plus a failed
  invoice for the small populations currently `past_due` or that churned
  `involuntary`ly exactly at a renewal boundary. No invoice is ever created
  for a trial that never converted (interval_id==0) -- nothing was ever
  charged, so there's nothing to invoice.
- Built directly on `subscription_events.csv`'s already-validated `renewed`
  events (reused, not recomputed) plus `build_subscription_objects()` for
  the subscription-level fields -- single source of truth for both.
- Real subtlety handled correctly rather than glossed over: 32 subscriptions
  have a single mid-life upgraded/downgraded tier change. A naive
  `invoices.plan_id = subscriptions.plan_id` would silently bill the WRONG
  (final) tier's price on every invoice issued before the change. Instead,
  each invoice gets its own plan_id based on whichever tier was actually in
  effect on its own date -- verified for all 32 affected subscriptions that
  pre-change and post-change invoices genuinely bill different amounts.
- **Caught two real bugs while validating** (both now fixed at the source,
  not papered over in invoices.csv):
  1. **A relativedelta month-end drift bug in invoice period math.**
     Computing each invoice's period_end by chaining "+1 month" off the
     previous invoice's date breaks under month-end clamping -- e.g. Jan 30
     -> Feb 28 -> chaining +1 month from Feb 28 lands on Mar 28, not the
     Mar 30 that computing directly from the origin date gives. This
     produced real 2-day gaps between consecutive invoice periods for
     subscriptions anchored on 29th/30th/31st-of-month dates crossing
     February. Fixed by computing every period boundary directly from the
     subscription's origin date at its own cycle index (matching how
     `subscriptions.py` already computes current_period_start/end), never
     by chaining off a previously-computed date. Same fix applied to the
     "does this involuntary churn land on a real renewal boundary" check.
     Contiguity check went from 6 breaks to 0.
  2. **A genuine cross-table logical contradiction, traced back to
     `subscription_events.csv` (already shipped)**: for a currently
     `past_due` subscription, the `renewed`-event loop was including the
     CURRENT cycle boundary (current_period_start) even though that exact
     renewal attempt is the one that's failing (that's the entire reason
     the subscription is past_due) -- producing a `renewed` event and a
     `payment_failed` event at the identical timestamp for the identical
     billing attempt, an impossible state (can't have both succeeded and be
     pending/failed). Fixed `build_subscription_events.py` to exclude that
     final cycle boundary specifically when status is `past_due`. Re-ran
     `validate_subscription_events.py` (with a matching fix to its own
     independent recomputation check) -- still 22/22, one fewer `renewed`
     event system-wide (2,423 total events, down from 2,424).
- `validate_invoices.py`: 24 checks across all 5 layers, including an exact
  paid-invoice-count reconciliation against subscription_events.csv's own
  renewed count (1,208 = 199 initial + 1,009 renewals), a perfect
  period-contiguity check across every subscription's invoice history (0
  gaps/overlaps), and exact-match counts for both failure-invoice types
  against their real preconditions (20 uncollectible = 20 aligned
  involuntary churns; 1 open = 1 past_due subscription). All 24 pass.
- **Phase 2 is now complete** (subscriptions, subscription_events, invoices
  -- all 3 tables built and cross-validated against each other and the
  master timeline).

## 2026-07-30 — Phase 3 begins: built + validated `discount_codes` (1 of 5)

- Ben said proceed into Phase 3 (orders, order_line_items, payments,
  refunds, discount_codes). Built `discount_codes` FIRST within the phase,
  even though schema_reference.md lists it last -- `orders.discount_code_id`
  will need real code definitions to redeem against, and discount_codes has
  no dependencies of its own, so the true build order is discount_codes ->
  orders -> order_line_items -> payments -> refunds, not the doc's listing
  order. Noted this explicitly rather than silently reordering.
- A small, hand-curated list of 7 codes (like products/subscription_plans
  were) -- not randomly generated, since these are business decisions, not
  simulated customer behavior. Mixes evergreen codes (WELCOME10, SAVE15,
  MERCH25OFF, COURSE20 -- no expiry) with time-boxed seasonal promos
  (HOLIDAY2024, and two separate one-off January codes in consecutive years,
  JANRESET10_2025 / JANRESET10_2026) -- thematically consistent with the
  project's already-established January seasonality spike that also drives
  win-back timing.
- `is_active` is deliberately derived, not hand-picked: True iff
  valid_until is null or still on/after END_DATE. All 3 seasonal codes'
  windows have already closed relative to END_DATE (2026-07-30), so they
  correctly come out `is_active=False` by construction, not by manually
  flagging them.
- `validate_discount_codes.py`: 19 checks. Real redemption-based checks (was
  a code only ever used inside its valid window, actual redemption rate)
  are deferred to `orders`, once it exists and can actually reference these
  codes -- noted in the docstring rather than faked here. All 19 pass.

## 2026-07-30 — Built + validated `orders` (2 of 5) -- and caught two real bugs, one all the way back in Phase 0

- Sourced from the timeline's `order_events` (known customers) plus the
  anonymous population's one-time guest merch purchases. Global
  chronological `order_id` across BOTH populations combined (not grouped by
  customer, unlike most other tables) -- a real storefront's order sequence
  isn't customer-grouped.
- Two things invented at this layer (discount codes and redemption don't
  exist in the master timeline): `subtotal` is reverse-matched against the
  exact price-tier list + discount formula `simulate_customers.py` already
  used (not float division, to avoid any rounding drift), and
  `discount_code_id`/`discount_code_amount` layer real `discount_codes.csv`
  redemptions onto otherwise-eligible orders at
  `ORDER_DISCOUNT_CODE_REDEMPTION_RATE` (12%).
- **Bug #1 -- a real business-rule violation traced back to Phase 0.**
  `validate_orders.py`'s central cross-check (no course order during an
  active subscription) is the first check in this whole project to test a
  Phase 3 table against Phase 2's real `subscriptions.csv` rather than just
  the internal timeline -- and it found 16 real violations. Root cause: the
  course_merch_only -> email-reactivation-conversion pathway generates a
  customer's organic order history BEFORE it's known whether (or when) the
  email trigger will convert them into a subscriber -- so that initial
  order generation necessarily uses `sub_windows=[]`. For the ~18 customers
  where the trigger DOES convert, some of those already-generated orders
  retroactively land inside the new subscription window, which didn't exist
  yet at generation time. Fixed with a new
  `_reconcile_orders_with_subscription_windows()` step in
  `simulate_customers.py`, run once sub_windows is finally known: any
  pre-existing COURSE order landing in the window is dropped (a hard
  violation), and any pre-existing MERCH order landing in the window is
  retroactively re-flagged `subscriber_discount_applied` and re-priced at
  the standard 20% discount (it was drawn at full price, not knowing a
  subscription would exist). This is a pure post-hoc filter -- it consumes
  zero additional random draws, so it doesn't perturb any other simulated
  value (confirmed: re-ran the full simulation and every headline number --
  98 active subscribers, 174 converted, 18 email-triggered conversions, 13
  still active -- came back byte-identical).
- **Bug #2 -- discovered while re-running Phase 0 to apply the fix above,
  and much more consequential: `pre_signup_anonymous_id` was generated with
  `uuid.uuid4()`, not the seeded rng.** uuid4() draws from `os.urandom`,
  completely invisible to (and unaffected by) the numpy seed -- meaning
  every rerun of `simulate_customers.py` mints a BRAND NEW anon_id for
  every one of the 860 customers, while every other simulated value stays
  identical. `devices.csv` and `identity_map.csv` were built from a
  PREVIOUS run's anon_ids, at a different time, by different scripts --
  so re-running the timeline for the order-reconciliation fix silently
  broke both of those already-shipped tables' exact-match validator checks
  (849/849 mismatches). This had been flagged as a known, "non-blocking"
  limitation back when `identity_map` was built (only ID uniqueness
  mattered, not exact reproducibility, or so it seemed) -- this is the
  first time the dataset actually needed a Phase-0 rebuild, and it showed
  that limitation was live, not cosmetic. Fixed at the root: replaced
  `uuid.uuid4().hex[:16]` with a deterministic hash of `customer_id`
  (`hashlib.md5`, zero rng draws, so it can't perturb anything else) in
  `simulate_customers.py`. Found and fixed the identical pattern in two
  more places while at it, for the same future-safety reason (neither was
  actively broken today, but both were the same latent landmine):
  `build_anonymous_population.py`'s ghost `anon_id` (code fixed; NOT
  regenerated, since nothing needed it and it would have pointlessly
  changed 17,050 already-fine IDs) and `build_devices.py`'s 2nd-device
  `anonymous_id` (fixed and regenerated, since devices.csv needed rebuilding
  anyway).
- Regenerated the timeline (2nd time, now with both fixes), then rebuilt
  `devices.csv` and `identity_map.csv` from it -- same exact row counts as
  before (18,042 / 992), only the anon_id strings changed shape (hash-based
  instead of random). **Re-ran every previously-shipped validator as a full
  safety sweep**: all 12 prior tables (products through discount_codes)
  still pass in full -- 18/18, 18/18, 19/19, 25/25, 21/21, 20/20, 17/17,
  23/23, 28/28, 22/22, 24/24, 19/19 -- confirming the two fixes changed
  nothing else in the dataset.
- Rebuilt `orders.csv` against the corrected timeline: 3,650 orders (down
  from 3,666 -- the 16 dropped course-during-subscription violations),
  $189,408.79 total revenue. `validate_orders.py`: 23 checks, including the
  now-passing cross-check against `subscriptions.csv` (0 violations, down
  from 16) and an exact row-count reconciliation against the timeline +
  anonymous population. All 23 pass.

## 2026-07-30 — Phase 3: build + validate order_line_items (3 of 5)

- `generator/build_order_line_items.py` -- `orders.csv` only ever carries an
  order-level amount (`subtotal`), never which specific product was bought;
  that's genuinely a line-item-level fact under normal order/order_line_item
  normalization (catalog facts live on the line item, order-level
  discounts/totals live on the order). This table resolves each order down
  to one specific `product_id` + `variant_id`.
- This simulated storefront never generates multi-item carts -- the master
  timeline tracks exactly one `order_type` + one `amount` per order event --
  so `order_line_items` is exactly one row per order, `quantity` is always 1,
  and `unit_price == line_total == subtotal` by construction.
- Product selection had one genuine ambiguity to resolve: each of the 5
  course price tiers maps to exactly one product, but the $24.99 merch tier
  maps to TWO products (Logo Cap vs. Water Bottle) -- resolved with a random
  pick between them per order. Variant selection: apparel products (Tee,
  Shorts, Pullover) have 4 size variants, picked with a size-distribution
  skew (S 20% / M 35% / L 30% / XL 15%, M/L most common); every other
  product has exactly one variant and needs no choice.
- `generator/validate_order_line_items.py` -- 5-layer suite, central checks
  being: exactly one line item per order (no multi-item carts, and every
  order_id in `orders.csv` is covered exactly once); every line item's
  product genuinely matches both its order's `order_type` AND its exact
  `subtotal` (i.e. the chosen product really does correspond to the priced
  tier, not just any random product of the right type); every variant
  actually belongs to its own product; and the real point of this table --
  per-order `sum(line_total)` reconciles exactly against `orders.csv`'s own
  `subtotal`.
- Result: 3,650 order_line_items (one per order, matching orders.csv
  exactly), all 12 catalog products represented (course products range from
  74 to 489 line items following the tier-price distribution baked into the
  timeline; merch products from 142 to 647, with the $24.99 tie between Cap
  (362) and Water Bottle (310) landing close to a 50/50 split as expected).
  `validate_order_line_items.py`: **14/14 checks passed on the first run** --
  no bugs found this time.

## 2026-07-30 — Phase 3: build + validate payments (4 of 5)

- `generator/build_payments.py` -- one row per Stripe-shaped Charge
  *attempt*, not one row per order. Every order in `orders.csv` represents a
  purchase that ultimately succeeded (no abandoned-cart concept in this
  dataset), but real storefronts routinely see a card declined and retried
  within the same checkout session -- that's the realistic messiness added
  here: a small share of orders (`ORDER_PAYMENT_ONE_RETRY_RATE` = 7%,
  `ORDER_PAYMENT_TWO_RETRY_RATE` = 1%) get 1 or 2 failed charge attempts
  immediately before the successful one -- same order_id/amount/currency,
  a fresh `payment_id` + `failure_code` each time, timestamped a few
  minutes before the successful charge (which itself is timestamped exactly
  at the order's own `created_at`). Every order gets exactly one succeeded
  payment by construction.
- Payment method (`card`/`paypal`/`apple_pay`, card brand, last4) is
  assigned independently per attempt rather than sticky across retries -- a
  customer switching payment methods mid-retry is realistic and not worth
  over-modeling.
- `generator/validate_payments.py` -- 5-layer suite, central checks being:
  every order has EXACTLY one succeeded payment (never zero, never two);
  every failed attempt's `processed_at` is strictly before its order's
  successful charge; the succeeded payment's amount matches the order's
  `total_amount` exactly; and `payments.customer_id` is null if and only if
  the order itself is a guest order.
- Result: 3,964 payments (3,650 succeeded + 314 failed retry attempts, i.e.
  7.7% of orders had at least one declined-then-retried attempt -- within
  the realistic 3-15% band checked distributionally). Payment method mix:
  86.5% card / 10.1% paypal / 3.5% apple_pay.
  `validate_payments.py`: **16/16 checks passed on the first run** -- no
  bugs found.

## 2026-07-30 — Phase 3: build + validate refunds (5 of 5) -- Phase 3 complete

- `generator/build_refunds.py` -- a small share of orders (`ORDER_REFUND_RATE`
  = 4.5%) later get refunded against their own succeeded payment, reused
  directly from `payments.csv` (never a failed attempt -- you can't refund a
  charge that never went through). Most refunds are full
  (`PARTIAL_REFUND_SHARE` = 25% are partial instead) -- a discretionary
  adjustment, since every order here is a single line item, not a
  partial-quantity return. `refunded_at` lands 1-21 days after `order_date`,
  clipped so it never lands after END_DATE; orders placed on END_DATE itself
  are excluded from refund eligibility entirely (no runway left in the
  dataset's observation window for a refund to land).
- `generator/validate_refunds.py` -- 5-layer suite, central checks being:
  every refund's `payment_id` is genuinely the SUCCEEDED payment for its own
  order; `refund.amount` never exceeds the order's `total_amount` (the
  "refund ≤ order total" convention documented in `generation_plan.md`);
  `refunded_at` is always after `order_date` and never after END_DATE; and
  at most one refund per order (no double refunds in this design).
- One validator bug caught and fixed during this build (not a data bug): the
  END_DATE boundary check initially compared full timestamps
  (`refunded_at <= pd.Timestamp(END_DATE)`, i.e. midnight), but
  `build_refunds.py` timestamps refunds at noon -- so a refund correctly
  landing ON END_DATE itself was flagged as "after" it. Fixed by comparing
  at calendar-date granularity (`refunded_at.dt.date <= END_DATE`), matching
  how END_DATE is used as a boundary everywhere else in this project (e.g.
  `devices.py`'s `last_seen_at`). The underlying data was correct all along;
  only the check's granularity was wrong.
- Result: 159 refunds (4.4% of all 3,650 orders -- within the realistic
  2-7% band checked distributionally), 116 full + 43 partial (27.0% partial
  share, within the configured 25% ± band), $6,546.82 total refunded.
  `validate_refunds.py`: **17/17 checks passed** after the one validator fix
  above.
- **Phase 3 is now complete**: discount_codes, orders, order_line_items,
  payments, refunds -- all 5 tables built, cross-validated against each
  other and against Phase 2's subscriptions.csv, and synced.

## 2026-07-30 — Phase 4: build + validate customer_segment_membership -- Phase 4 complete

- `generator/build_customer_segment_membership.py` -- effective-dated
  (entered_at/exited_at) membership rows for the 9 customer-grain segments
  in segments.csv, computed ENTIRELY from already-shipped behavioral data
  (subscriptions.csv, orders.csv, invoices.csv, customers.csv) -- nothing
  invented independently, per schema_reference.md's explicit requirement.
  Anonymous-device segments (18 of the 27 total) never get rows here.
- **seg_009 ("High Churn Risk") is deliberately skipped, 0 rows.**
  segments.csv's own description says its engagement half depends on Phase
  5 (real usage-event recency/frequency), which doesn't exist yet --
  computing it now would mean inventing the missing signal, exactly the
  kind of independently-invented data this project's whole design avoids.
  It'll be built once Phase 5 ships real session/event data.
- Design decision worth calling out: seg_002/003/004 (the "Lapsed N Days"
  ladder) and seg_008 ("Lapsed - Still Buying") apply to ANY canceled
  subscription object, not just real (converted) intervals -- a trial that
  simply expired or was canceled sets `canceled_at` exactly the same way a
  real interval's cancellation does, and segments.csv's own wording doesn't
  restrict itself to paid intervals. A customer whose trial never converted
  still enters the lapsed ladder at their trial's own cancellation date;
  they just never pass through seg_001 (Active Subscriber) first.
- seg_001 -> one row per real interval (entered_at=start_date,
  exited_at=canceled_at). seg_002/003/004 -> a 0-30/31-90/90+ day ladder
  per canceled object, each tier's exit clipped to the EARLIEST of its
  natural day boundary or the customer's next subscription object starting;
  a tier still open as of END_DATE gets exited_at=null and no later tier is
  emitted (this is a point-in-time snapshot, not a log of future-scheduled
  transitions). seg_005 -> only for customers with a genuine gap between
  signup and their first subscription object (the 309 who never subscribed
  at all, permanently, plus the 38 merch-to-sub-email customers,
  temporarily) -- the 513 customers whose very first behavior IS starting a
  trial never get a row, since they were never actually in that state.
  seg_006 -> direct filter on status=='trialing' (3 rows). seg_007 ->
  lifetime revenue (orders + paid invoices) in the top decile of the
  eligible customer base, entered_at = the date each customer's own
  running cumulative revenue first crosses the threshold. seg_008 -> a
  qualifying course/merch order landing strictly between a cancellation and
  the customer's next subscription object (if any).
- Soft-deleted customers (11 of 860) get ZERO rows -- same full-erasure
  treatment already applied to customer_addresses.csv and devices.csv, since
  this is a marketing/segmentation table, not a transactional record needing
  referential-integrity preservation.
- One real bug caught and fixed during this build: the initial implementation
  only iterated `subscriptions.csv` grouped by customer_id, which silently
  skipped the 309 customers who have ZERO subscription rows at all --
  meaning they got no seg_005 row despite being the clearest possible case
  of "never subscribed." Caught by eyeballing the first build's output
  (seg_005 = 38, suspiciously exactly the merch-to-sub-email count with the
  309 "true" never-subscribed customers missing entirely). Fixed by handling
  that population as an explicit separate pass before the per-subscription
  loop.
- One validator bug caught and fixed (not a data bug, same class as the
  refunds-table fix earlier this session): the "entered_at is never before
  signup" check initially compared full timestamps, but `trial_start` is a
  date-only field stored at midnight while `customers.created_at` carries a
  real time-of-day -- so a trial starting the same calendar day as signup
  (the normal case) looked like it started "before" signup purely from
  midnight being earlier than the actual signup time. Fixed to compare at
  calendar-date granularity.
- Result: 2,234 rows across 8 of 9 customer-grain segments (seg_001: 197,
  seg_002: 465, seg_003: 454, seg_004: 411, seg_005: 347, seg_006: 3,
  seg_007: 85, seg_008: 272). seg_007 (High-LTV) lands at exactly 10.0% of
  the eligible customer base, matching its top-decile design intent.
  `validate_customer_segment_membership.py`: **16/16 checks passed** after
  the one validator fix above, including seg_001's entered_at dates and row
  count reconciling exactly against subscriptions.csv's own real intervals,
  and seg_006's row count matching the trialing-status count exactly.
- **Phase 4 is now complete** (its only table).

## 2026-07-30 — Phase 5: build + validate web_sessions (1 of 4)

- `generator/build_web_sessions.py` -- marketing-site/storefront browsing
  sessions (NOT in-app fitness usage -- that's app_sessions/app_events,
  later in this phase). Two populations, both derived from already-decided
  ground truth rather than invented independently:
  - **Anonymous ghosts (17,050)**: `_sim_anonymous_population.csv` already
    carries `num_sessions` (decided back in Phase 0) and `channel` per
    ghost -- this table just realizes those exact counts as real session
    rows. Guest purchasers' LAST session lands exactly on their
    `guest_purchase_date`, so `web_events` (table 2 of 4) has a session to
    hang a `purchase` event off later.
  - **Known, non-deleted customers**: 1-3 pre-signup sessions (same
    distributional shape as the ghost population), the last of which is the
    exact signup moment (`customer_id` populates from that session onward,
    never before); a session on every `reactivations` win-back date
    (utm_source = that event's own channel); a session on every
    known-customer order date; plus tier-driven "filler" organic browsing
    sessions across their active tenure (power > regular > casual) --
    THE Phase 5 usage signal generation_plan.md's cross-phase commitment #2
    requires. app_sessions/app_events (later in this phase) must size their
    own volume off this same `engagement_tier`, not invent a separate signal.
  - Soft-deleted customers (11) get zero rows, same full-erasure treatment
    as customer_addresses.csv/devices.csv. Only new-acquisition and
    reactivation sessions carry real UTM attribution; every return-visit
    and filler session is organic/direct (utm fields null), matching how
    real web analytics only attributes new/re-marketing traffic.
- `generator/validate_web_sessions.py` -- 5-layer suite, central checks
  being: unique anonymous_id count exactly equals eligible customers +
  ghosts (17,899 = 17,899, nothing invented or dropped); customer_id is
  null before signup and populated from the signup session onward, never
  null again after; every known-customer order has a same-day session;
  every ghost's own session count matches `num_sessions` exactly; and every
  guest purchaser's last session lands exactly on `guest_purchase_date`.
- Two real bugs caught and fixed during this build:
  1. Guest purchasers with exactly 1 session had that session placed on
     `first_seen_date` unconditionally, even when their purchase happened
     days later (mean gap ~6.7 days, up to 13) -- meaning their one and
     only session missed the actual purchase day entirely. Fixed to place
     a single session directly on `guest_purchase_date` when there's only
     one to place.
  2. A `.gamma()`-distributed session duration produced fractional-second
     `ended_at` timestamps, creating a mixed-precision timestamp column
     (some rows with microseconds, most without) that pandas couldn't parse
     with one format string. Fixed by rounding session duration to whole
     seconds -- also caught a latent `rng.choice(..., replace=False)` crash
     risk for guest purchasers with a same-day (gap=0) purchase and 3
     sessions (3 real cases in the data), fixed with a capped/padded
     offset-sampling approach.
- Result: 30,285 web_sessions (6,476 identity-resolved to a customer_id,
  23,809 anonymous-only). Device category split: 54.5% mobile / 40.3%
  desktop / 5.5% tablet (mobile-dominant, matching the fitness-app-skews-
  mobile assumption already used for devices.csv). `validate_web_sessions.py`:
  **13/13 checks passed** after the two fixes above.

## 2026-07-30 — Phase 5: build + validate web_events (2 of 4)

- `generator/build_web_events.py` -- page-level events within each
  web_sessions.csv row: page_view/product_view/add_to_cart/begin_checkout/
  purchase/search, per schema_reference.md's vocabulary. The central
  guarantee: EVERY row in orders.csv (excluding soft-deleted customers'
  orders, which have zero web_sessions rows by design) gets exactly one
  `purchase` event, attached to a real session that both belongs to the
  right identity and falls on the order's own order_date -- reusing
  web_sessions.csv's own already-validated same-day-session invariants
  rather than re-deciding session timing here.
- Two real linkage problems solved to make that guarantee work, since
  neither orders.csv nor web_sessions.csv carries a direct FK to the other:
  (1) a customer with 2+ orders the same day has 2+ same-day sessions too,
  with nothing on disk saying which belongs to which -- resolved by pairing
  sessions (sorted by started_at) against orders (sorted by order_id)
  within each (customer_id, date) group; (2) guest orders' `guest_email` is
  randomly generated at build time with no link back to the originating
  ghost, and 276 of the 1,257 guest purchasers collide with another ghost
  on the only shared key (order_date, subtotal) -- resolved with a
  candidate-order_id queue per key, popped one-per-ghost in the anonymous
  population's own deterministic row order. Collisions are provably
  interchangeable (identical date + amount), so any pairing within one is
  equally correct.
- Every purchase event's product_id is the customer's ACTUAL purchased
  product, pulled from order_line_items.csv (single source of truth), not
  re-decided independently.
- `generator/validate_web_events.py` -- 5-layer suite, central checks being:
  every eligible order has exactly one purchase event; every purchase
  event's product_id matches order_line_items.csv exactly; every event's
  occurred_at falls within its own session's time window; and every
  known-customer purchase event's session genuinely belongs to that same
  customer (the pairing logic never cross-wires two different customers).
- One real bug caught and fixed during this build: the timestamp-spacing
  helper called `np.random.default_rng()` fresh on every invocation instead
  of using the shared seeded rng -- an unseeded, non-reproducible entropy
  source that would silently break this script's reproducibility (a rerun
  with the same seed would produce different event timestamps every time).
  Caught by re-reading the draft before running it. Fixed by threading the
  shared rng through explicitly.
- One validator-calibration issue caught and fixed (not a data bug): the
  cart-abandonment distributional check's expected band (0.5-4%) was a
  guess that didn't match the build's own `CART_ABANDON_RATE` parameter (6%
  of non-purchase sessions, which works out to ~5% of all sessions once
  scaled by the ~88% of sessions that never purchase). Widened the band to
  3-8% to match the actual designed rate rather than an arbitrary guess.
- Result: 117,706 web_events (70,302 page_view, 30,211 product_view, 5,294
  add_to_cart, 4,211 begin_checkout, 4,055 search, 3,633 purchase -- 3,633
  vs. orders.csv's 3,650 rows, the 17-row gap being exactly the orders
  belonging to soft-deleted customers). `validate_web_events.py`: **15/15
  checks passed** after the two fixes above.

## 2026-07-30 — Phase 5: build + validate app_sessions (3 of 4)

- `generator/build_app_sessions.py` -- in-app fitness usage (NOT the
  marketing/storefront browsing already covered by web_sessions).
  customer_id is always present here (the app requires being logged in;
  there's no anonymous app usage in this dataset), and there's no UTM
  attribution. Two independent, non-invented reasons a customer gets rows:
  1. **Real subscription intervals** (the same population as
     customer_segment_membership's seg_001) get ongoing sessions across
     [start_date, canceled_at-or-END_DATE], at a weekly rate keyed by
     `engagement_tier` (power/regular/casual) -- the direct fulfillment of
     generation_plan.md's cross-phase commitment #2: usage volume must be
     sized off the SAME engagement signal already driving segment
     membership and web_sessions' filler browsing volume, not a separately
     invented one. Usage stops the moment a subscription lapses.
  2. **Course orders** (any known, non-deleted customer, independent of
     subscription status) get a burst of 3-10 sessions in the 45 days after
     the order date, working through the purchased content.
  Merch-only customers get zero rows (nothing to access in-app). Every
  session is pinned to the customer's PRIMARY device (devices.csv's first
  row per customer_id) and `platform` mirrors that device's own
  device_type exactly, never independently re-rolled.
- `generator/validate_app_sessions.py` -- 5-layer suite, central checks
  being: every session's device_id genuinely belongs to that same
  customer_id in devices.csv; platform matches that device's device_type
  exactly; every session date falls inside either a real subscription
  interval or a course's 45-day access window for that customer (no usage
  invented with no underlying reason); and customers with neither a real
  subscription interval nor a course order get zero rows.
- One validator-calibration issue caught and fixed (not a data bug): the
  "distinct customers with usage" check initially required an EXACT match
  against the eligible population, but 5 casual-tier subscribers with
  ~1-month tenure legitimately drew zero sessions from the Poisson process
  (~18% chance of zero opens before churning at that rate/tenure combo) --
  a realistic "signed up, barely used it, canceled" outcome, not a bug.
  Loosened to a small tolerance band instead of an exact match.
- Result: 19,610 app_sessions across 496 of 501 eligible customers (496 vs
  501 -- the 5-customer gap being exactly those legitimate zero-usage
  churners). Platform mix (40.3% ios / 34.2% android / 25.5% web) lands
  within 10 points of the overall device population's own mix.
  `validate_app_sessions.py`: **12/12 checks passed** after the one fix
  above.

## 2026-07-30 — Phase 5: build + validate app_events (4 of 4) -- Phase 5 complete

- `generator/build_app_events.py` -- fitness-specific event vocabulary
  within each app_sessions.csv row: `class_started` (near the session's own
  started_at, picking a workout_type from a 7-type taxonomy),
  `workout_completed` or `workout_abandoned` (exactly one of the two, near
  ended_at or partway through the session for abandons -- 85% complete),
  and `streak_achieved`.
- `streak_achieved` is NOT randomly sprinkled -- it's computed from each
  customer's own REAL distinct session dates in app_sessions.csv
  (consecutive-day runs, no gap). The first session on the day a run first
  reaches one of 3/7/14/30/60/100 days gets the event with that exact
  streak_days value. Every streak is independently re-derivable from
  app_sessions.csv alone.
- `generator/validate_app_events.py` -- 5-layer suite, central checks
  being: every session has exactly one class_started and exactly one of
  workout_completed/workout_abandoned; workout_completed's duration_minutes
  matches that session's real duration exactly; and -- the most important
  check in this table -- streak_achieved events are independently
  RE-DERIVED in the validator from app_sessions.csv's own dates and checked
  for an EXACT match against the build's output, proving the streak signal
  is genuinely computed, not invented.
- One real bug caught and fixed proactively during this build (same class
  already fixed twice this phase, in web_sessions.csv and web_events.csv):
  `workout_abandoned`'s timestamp was computed as
  `started_at + duration * a_float_fraction`, producing fractional-second
  timestamps that would have broken pandas' single-format datetime parsing
  the same way. Recognized the pattern from the earlier fixes and rounded
  to whole seconds before the first validation run, rather than discovering
  it via a crash again.
- Result: 39,370 app_events (19,610 class_started, 16,580
  workout_completed, 3,030 workout_abandoned, 150 streak_achieved -- 125 at
  the 3-day threshold, 25 at 7-day; nobody in this dataset strings together
  a real 14+ consecutive-day streak, which is itself a realistic outcome of
  Poisson-scattered session dates rather than guaranteed-daily attendance).
  `validate_app_events.py`: **15/15 checks passed on the first validation
  run** (after the proactive fix above).
- **Phase 5 is now complete**: web_sessions, web_events, app_sessions,
  app_events -- all 4 tables built, cross-validated against each other and
  against Phase 2/3's subscriptions/orders, with app usage volume
  consistently keyed off the same `engagement_tier` signal throughout, per
  generation_plan.md's cross-phase commitment #2.

## 2026-07-30 — Phase 6: build + validate braze_email_campaigns (1 of 4)

- `generator/build_braze_email_campaigns.py` -- built first within Phase 6,
  same reason discount_codes came first in Phase 3: braze_email_events
  (table 2 of 4) needs real campaign definitions to send against. A small,
  hand-curated list (like discount_codes/segments/subscription_plans were)
  -- 9 campaigns, 7 triggered + 2 broadcast.
  - Triggered campaigns each name a `trigger_event` that maps to a REAL
    source already sitting in an earlier phase's shipped tables: trial
    starts (subscriptions.csv), trial-ending reminders, payment failures
    (subscription_events.csv), win-back reactivations whose true channel is
    email (the master timeline's `reactivations` list -- same field
    web_sessions.csv already used), the merch-to-subscriber pathway's
    actual triggering send, order confirmations (orders.csv), and
    abandoned-cart reminders (web_events.csv's add_to_cart-without-purchase
    sessions). braze_email_events.py will derive real send volume from
    these sources, not invent recipients independently.
  - The two broadcast campaigns aren't tied to individual behavior --
    "Monthly Newsletter" is a recurring calendar send, and "Seasonal Sale
    Promo" is deliberately timed to discount_codes.csv's own
    HOLIDAY2024/JANRESET10_2025/JANRESET10_2026 valid windows, since those
    are the real codes such a promo would be advertising.
- `generator/validate_braze_email_campaigns.py` -- lighter-weight
  definitions-table validation (same class as discount_codes.csv/
  segments.csv's own validators): trigger_event drawn from a closed,
  derivable vocabulary; no two campaigns claiming the same trigger (which
  would make the next table's derivation ambiguous).
- Result: 9 campaigns. `validate_braze_email_campaigns.py`: **10/10 checks
  passed** on the first run.

## 2026-07-30 — Phase 6: build + validate braze_email_events (2 of 4)

- `generator/build_braze_email_events.py` -- dot-path event_type naming
  (`users.messages.email.Send/.Open/.Click/.Bounce/.Unsubscribe`). Every
  send traces to a real source in an earlier phase's shipped tables, keyed
  off braze_email_campaigns.csv's own `trigger_event` vocabulary: every
  trial object in subscriptions.csv (welcome + ~2-days-before-end
  reminder), every deduped payment_failed row in subscription_events.csv,
  the master timeline's own email-channel reactivations, the
  merch-to-subscriber pathway's actual triggering send (same
  signup-vs-trial_start gap customer_segment_membership.py's seg_005 uses),
  every order in orders.csv (known-customer AND guest -- the one place
  external_user_id is "almost" always populated, guests being the
  exception), and web_events.csv's known-customer add_to_cart-without-
  purchase sessions. Plus 2 broadcast sends (Monthly Newsletter every
  month, Seasonal Sale Promo on discount_codes.csv's own real promo dates)
  to the opted-in, non-deleted customer base that existed as of each send
  date. Soft-deleted customers are excluded from every population, same
  full-erasure treatment as customer_addresses/devices/web_sessions/
  app_sessions.
- Each send gets its own `send_id`, shared across that send's funnel events
  -- without it, two sends of the same recurring broadcast campaign to the
  same customer (different months' newsletters) would be ungroupable and
  funnel ordering unverifiable from the shipped table alone. Caught this
  gap while designing the table, before shipping it.
- `generator/validate_braze_email_events.py` -- 5-layer suite, central
  checks being: every send_id has exactly one Send event and every
  Open/Click/Bounce/Unsubscribe for it occurs strictly after that Send;
  external_user_id is null ONLY for order_placed's guest sends; and two
  exact-count reconciliations against real source tables --
  order_placed's Send count vs. orders.csv's own eligible row count
  (3,633 = 3,633) and payment_failed's Send count vs.
  subscription_events.csv's own deduped count (86 = 86).
- **One real bug caught and fixed retroactively in a Phase 5 table**: while
  building this table, mixing web_events.csv's own timestamps into a new
  column alongside whole-second timestamps elsewhere broke pandas' single-
  format datetime parsing -- tracing it back revealed `build_web_events.py`'s
  `_spaced_timestamps()` had never actually been fixed for fractional
  seconds (only its earlier unseeded-rng bug was) -- every one of
  web_events.csv's 117,706 rows carried a fractional-second timestamp. This
  was invisible to web_events.csv's own validator (one consistent
  fractional format parses fine in isolation) and only surfaced once a
  second table needed to mix timestamp sources. Fixed at the source
  (offsets now rounded to whole seconds before use), rebuilt web_events.csv
  (same 117,706 rows, same event-type breakdown, same purchase-event
  reconciliation -- `validate_web_events.py` still 15/15), then rebuilt
  braze_email_events.csv against the corrected file.
- Result: 26,328 braze_email_events (18,187 sends: 6,322 opens, 1,341
  clicks, 356 bounces, 122 unsubscribes -- 34.8% open rate, 2.0% bounce
  rate, both in realistic email-marketing ranges). 8.2% of all rows have a
  null external_user_id, exactly the guest-order-confirmation share.
  `validate_braze_email_events.py`: **13/13 checks passed** after the
  web_events.csv fix.

## 2026-07-30 — Phase 6: build + validate braze_push_campaigns (3 of 4)

- `generator/build_braze_push_campaigns.py` -- built before the push events
  table needs it, same reasoning as every other campaigns-then-events
  pairing in this project. A push-appropriate SUBSET of triggers, not a
  blind mirror of the 9 email campaigns -- push fits different moments
  (streak celebrations, urgent re-engagement) and doesn't fit others
  (nobody expects an abandoned-cart push; guests have no device to push to
  at all, so push's order_placed campaign is deliberately narrower in
  scope than email's, known-customers-only).
  - Triggered (5): Trial Ending Reminder (push variant of email's),
    Payment Failed (urgent enough for both channels), Win-Back Lapsed
    Subscriber (filtered to the master timeline's channel=='push'
    reactivations -- may realistically be a quiet campaign if that
    population is small or empty in this dataset's specific draw), Streak
    Celebration (ties directly to app_events.csv's streak_achieved), Order
    Shipped (known customers only).
  - Broadcast (2): New Class Launch (occasional) and Weekly Motivation
    Push (higher cadence than email's monthly newsletter -- push is
    cheaper and lower-friction, realistically).
- `generator/validate_braze_push_campaigns.py` -- same lightweight
  definitions-table validation class as braze_email_campaigns.csv.
- Result: 7 campaigns. `validate_braze_push_campaigns.py`: **11/11 checks
  passed** on the first run.

## 2026-07-30 — Phase 6: build + validate braze_push_events (4 of 4) — Phase 6 complete

- `generator/build_braze_push_events.py` -- final Phase 6 table. Same
  dot-path `users.messages.pushnotification.*` naming as email, with
  `device_id`/`platform` in place of `email_address`. Reuses the same real
  source populations braze_email_events.py established (trial_ending and
  payment_failed from subscriptions.csv/subscription_events.csv;
  reactivation from the master timeline, this time filtered to
  `channel == "push"`; order_placed from orders.csv, but known-customers
  ONLY since guests have no device to push to) plus one population with no
  email analog: streak_achieved, sourced directly from app_events.csv's
  own streak_achieved milestones, tying this table directly to Phase 5.
  Two broadcasts: New Class Launch (6 fixed calendar dates) and Weekly
  Motivation Push (bi-weekly, but only a random 40% sample of the eligible
  list per send -- realistic frequency capping, since no real push
  provider blasts its whole opted-in base every two weeks forever).
- **`push_opt_in` is a hard delivery precondition, not just a marketing
  filter**: every triggered and broadcast send is gated on
  `push_opt_in == True` before it's ever generated. This is a deliberate
  asymmetry from email, where a transactional message can always
  technically be attempted against an address on file -- push requires an
  OS-level permission grant, so a customer who never granted it
  categorically cannot receive one.
  Every send is pinned to the customer's PRIMARY device (devices.csv's
  first row per `customer_id`, the same convention app_sessions.csv
  already established), and `platform` mirrors that device's own
  `device_type` exactly.
- Reused the `send_id` design from braze_email_events.py (one send_id per
  send, shared across its own funnel events) from the start, having
  already learned that lesson mid-build on the email table.
- `generator/validate_braze_push_events.py` -- 19-check, 5-layer suite.
  Central checks: exactly one Send per send_id and every
  Open/Click/Bounce/Unsubscribe strictly after its own Send;
  external_user_id is NEVER null (push, unlike email, has no
  guest-checkout case); every external_user_id on every row has
  `push_opt_in == True` in customers.csv; device_id/platform are
  internally consistent with devices.csv's own primary-device convention;
  and two exact-count reconciliations against real source tables --
  order_placed's Send count vs. orders.csv's own eligible (known-customer
  + push-opted-in + has-a-device) row count (1,049 = 1,049) and
  streak_achieved's Send count vs. app_events.csv's own streak_achieved
  population for push-opted-in customers (74 = 74). Also checked
  proactively for the fractional-second timestamp bug class that recurred
  multiple times earlier this session (web_sessions, web_events) -- clean
  on this table from the start.
- Result: 9,897 braze_push_events (7,851 sends: 1,590 opens, 220 clicks,
  205 bounces, 31 unsubscribes -- 20.3% open rate, 2.6% bounce rate, both
  in realistic push-marketing ranges, and both directionally consistent
  with push trailing email on opens and running higher on bounces).
  `validate_braze_push_events.py`: **19/19 checks passed on the first
  run** -- no bugs found in this table.
- **Phase 6 complete** (all 4 tables: braze_email_campaigns,
  braze_email_events, braze_push_campaigns, braze_push_events). 25 of 47
  tables now shipped. Phase 7 (paid media: Meta, Google Search, YouTube,
  DV360, Snap, TikTok) is next, pending further instruction.

## 2026-08-13 — Phase 7: build + validate Meta (1 of 6 paid-media platforms)

- Phase 7 is 22 tables across 6 platforms (schema_reference.md), the last
  phase. Working unit for this phase is **one platform at a time** rather
  than one table at a time (still fully built + validated table by table
  within each platform) -- otherwise this would be 22 separate sync
  cycles for tables that are only ever meaningful together.
- **New shared design, since ad-platform tables have NO user-level join to
  our own data** (schema_reference.md is explicit about this -- attribution
  only via UTM on web_sessions): rather than exact-count reconciliation
  (the Braze pattern), Phase 7 tables are validated by confirming their
  spend/volume tracks the SAME underlying levers that already drove
  web_sessions.csv's own per-channel session volume --
  `_sim_seasonality_calendar.csv`'s weekly demand multiplier and
  `_sim_channel_mix_schedule.csv`'s per-channel weekly share. New shared
  helper `generator/paid_media_common.py` centralizes this for all 6
  platforms' daily performance tables.
- `generator/build_meta_campaigns.py` -- 7 campaigns: 4 evergreen
  (prospecting/retargeting/lookalike/conversion, always-on for the full
  3-year window, daily_budget-paced) + 3 flighted brand_lift campaigns
  timed near BFCM each year (lifetime_budget-paced, COMPLETED status),
  which is how real brand-lift awareness studies actually run -- short
  bursts, not an always-on line item.
- `generator/build_meta_ads.py` -- functions as the ad-set-level entity
  (targeting, optimization_goal) since Meta's real Campaign > Ad Set > Ad
  hierarchy collapses to just meta_campaigns/meta_ads here
  (schema_reference.md lists no separate ad_sets table). 10 ads total.
  targeting_segment_id populated only for retargeting (split across its 2
  ads: one per segments.csv's "Website Visitors" / "Cart Abandoners"
  Meta segment) and lookalike (segments.csv's Meta lookalike segment) --
  prospecting/conversion/brand_lift stay broad.
- `generator/build_meta_ad_insights_daily.py` -- 7,396 rows. Each day's
  total Meta spend = `BASE_DAILY_AD_SPEND_TOTAL x seasonality multiplier x
  meta's channel-mix share x lognormal noise`, split across the 4
  evergreen objectives by fixed weight (summing to exactly 1.0) then
  across that objective's ads; brand_lift flights spend their own
  lifetime_budget independently across their own flight days.
  **One real bug caught before shipping**: `lifetime_budget` is stored in
  cents (Meta API convention, same as `daily_budget`), but the brand_lift
  daily-spend split initially divided it directly without converting to
  dollars -- inflated 3 flights' realized spend to ~$1.13M against a
  combined $11,300 in declared budgets (a ~100x overshoot, and it pushed
  total Meta spend to $1.55M against an expected ~$440-450K). Caught by
  sanity-checking the printed total against a hand-computed expectation
  before writing the validator, not by the validator itself -- fixed the
  cents-to-dollars conversion and recalibrated `META_DAILY_BUDGET_CENTS`
  to match what the seasonality/mix formula actually realizes for a
  typical (non-peak) day. Rebuilt: total Meta spend now $429,401 (blended
  $12.11 CPM, 1.52% CTR -- both in realistic paid-social ranges).
- `generator/build_meta_ad_actions_daily.py` -- 35,504 rows. Derived
  DIRECTLY from meta_ad_insights_daily.csv's own clicks/impressions (not
  independently redrawn), same "derive from an already-shipped upstream
  table" pattern app_events.py used for streak_achieved -- guarantees the
  click-driven funnel (link_click -> landing_page_view -> add_to_cart ->
  initiate_checkout -> purchase) is monotonically non-increasing by
  construction. **Funnel conversion rates recalibrated before shipping**
  after a first pass produced 19,249 self-attributed "purchase" actions
  from Meta ALONE -- ~5x the business's entire actual purchase volume
  across all channels combined (3,849), which would have made summing all
  6 platforms' claimed purchases absurd. Retuned to land Meta's total at
  6,543 claimed purchases (1.70x actual total real purchases) -- a
  believable single-platform over-attribution multiple (real ad
  platforms' pixels do over-claim vs. site-side truth via multi-touch
  overlap and generous attribution windows, just not by 5-20x).
- Validation: `validate_meta_campaigns.py` 13/13, `validate_meta_ads.py`
  10/10, `validate_meta_ad_insights_daily.py` **17/17 (includes two
  correlation checks: weekly Meta spend vs. web_sessions.csv's own
  meta-attributed weekly session count, Pearson r=0.678 across 157 weeks;
  and weekly spend vs. the underlying seasonality x channel-mix formula
  directly, r=0.919 -- confirms the daily noise/pause layer didn't drown
  out the cross-phase signal)**, `validate_meta_ad_actions_daily.py`
  12/12. **52/52 checks passed across all 4 Meta tables.**
- Meta (1 of 6 Phase 7 platforms) complete. 29 of 47 tables now shipped.
  Next: Google Search.

## 2026-08-13 — Phase 7: build + validate Google Search (2 of 6 paid-media platforms)

- `generator/build_google_search_campaigns.py` -- 5 evergreen campaigns
  (one per objective, same 5-objective vocabulary as Meta). Unlike Meta,
  ALL 5 are always-on here, including the brand_lift analog ("Search -
  Brand Term Defense") -- a real search advertiser never pauses bidding on
  their own brand name the way a flighted awareness study pauses, so
  making it evergreen (not a flight) is the more realistic choice for this
  platform specifically. Documented as a deliberate platform-specific
  divergence from Meta's pattern, not an inconsistency.
- `generator/build_google_search_ad_groups.py` -- 8 ad groups.
  targeting_segment_id populated only for the 2 RLSA (retargeting) ad
  groups (segments.csv's Google Search "Website Visitors" / "Cart
  Abandoners") and the 1 similar-audiences (lookalike) ad group.
- **Build order deliberately inverted from schema_reference.md's listed
  table order**: built `google_search_keyword_performance_daily` (the
  granular, keyword-level ground truth -- no separate keywords dimension
  table exists in the schema, so each ad group's 2-4 keywords are defined
  once in-script and reused deterministically across every day) BEFORE
  `google_search_performance_daily`, then derived the latter as an EXACT
  aggregation up to ad_group/day grain. Same "derive the coarser table
  from an already-shipped finer one" reasoning used for meta_ad_actions,
  just inverted since here the finer grain is the one schema lists second.
  This guarantees the two tables reconcile exactly, checked as an
  exact-count business-rule check (not a plausibility band) in
  `validate_google_search_performance_daily.py`.
- Same seasonality-calendar x channel-mix-schedule spend driver as Meta,
  via the shared `paid_media_common.py` helpers -- google_search's own
  ~20% average channel share.
- **One calibration adjustment made before shipping** (informed directly
  by the Meta over-attribution lesson): a first pass at
  `GOOGLE_SEARCH_CONVERSION_RATE_BY_OBJECTIVE` produced 12,038
  self-attributed conversions -- 3.13x the business's actual total real
  purchases (3,849), just outside the believable single-platform range
  established for Meta (1.70x). Retuned down ~25% to 9,297 claimed
  conversions (2.42x) before ever running the validator, since search's
  higher intent legitimately supports a somewhat higher ratio than paid
  social's.
- Validation: `validate_google_search_campaigns.py` 11/11,
  `validate_google_search_ad_groups.py` 10/10,
  `validate_google_search_keyword_performance_daily.py` **17/17
  (includes the same weekly-spend-vs-web_sessions correlation check
  pattern as Meta's, Pearson r=0.681 across 156 weeks)**,
  `validate_google_search_performance_daily.py` **11/11 (central check:
  every ad_group/day row's impressions/clicks/cost_micros/conversions
  reconcile EXACTLY against the sum of that ad_group/day's own keyword
  rows -- $350,535.12 total cost matches to the penny at both grains)**.
  **49/49 checks passed across all 4 Google Search tables.**
- Google Search (2 of 6 Phase 7 platforms) complete. 33 of 47 tables now
  shipped. Next: YouTube.

## 2026-08-13 — Phase 7: build + validate YouTube (3 of 6 paid-media platforms)

- `generator/build_youtube_campaigns.py` -- 7 campaigns, structurally
  mirroring Meta (4 evergreen + 3 flighted brand_lift near BFCM) rather
  than Google Search's all-evergreen pattern, because YouTube Brand Lift
  is a real, commonly-run Google measurement product delivered via
  bumper/non-skippable formats -- a flighted study is the realistic choice
  here, unlike Search's always-on brand-term defense.
- `generator/build_youtube_ad_groups.py` -- 9 ad groups, same
  targeting_segment_id discipline as every other platform (retargeting
  splits across 2 ad groups, one per YouTube retargeting segment;
  lookalike gets 1 targeted ad group; everything else broad).
- `generator/build_youtube_performance_daily.py` -- 6,394 rows. Video
  economics modeled cost-per-view-first (spend -> video_views ->
  impressions via view_rate -> clicks via a small companion-banner rate),
  the inverse of Meta's impression-first model, since that's what
  TrueView/bumper billing actually optimizes for. Bumper/non-skippable
  brand_lift rows get a much higher realized video_view_rate (0.85-0.98)
  than skippable TrueView objectives (0.20-0.35) -- unskippable formats
  count nearly every impression as a view.
- **One real bug caught by the validator itself** (not just a pre-emptive
  sanity check this time): `validate_youtube_performance_daily.py`'s
  weekly-spend-vs-web_sessions correlation check FAILED on the first run
  (r=0.338, below the 0.4 threshold). Investigation traced it to
  `YOUTUBE_BRAND_LIFT_FLIGHTS`' lifetime budgets -- copied at roughly
  Meta's dollar scale ($12-14K/flight) without rescaling for YouTube's
  much smaller ~9% average channel share (vs. Meta's ~24%), so each
  18-day flight was injecting spend at ~4.4x YouTube's own evergreen daily
  baseline (vs. Meta's flights running at a proportionate ~1.2x) -- three
  huge, formula-unexplained spikes per year overwhelming a 156-week
  correlation. A second bug surfaced while fixing the first: rebuilding
  `youtube_performance_daily.csv` alone after editing the budget in
  params.py produced NO change at all, because the daily build script
  reads `lifetime_budget_micros` from the already-shipped
  `youtube_campaigns.csv` file, not from params.py directly --
  `youtube_campaigns.csv` had to be rebuilt first. Rescaled the flight
  budgets to ~$2,500-2,900 (proportionate to Meta's flight/baseline
  ratio), rebuilt campaigns -> ad_groups -> performance_daily in that
  order: correlation recovered to r=0.625, total YouTube spend dropped
  from $199,689 to a more sensible $170,407.
- Validation: `validate_youtube_campaigns.py` 14/14,
  `validate_youtube_ad_groups.py` 11/11,
  `validate_youtube_performance_daily.py` **13/13 (after the fix above;
  includes a check that brand_lift's view_rate is structurally much
  higher than the skippable objectives', and the weekly spend-vs-
  web_sessions correlation, r=0.625 across 156 weeks)**. **38/38 checks
  passed across all 3 YouTube tables** (after the mid-build fix).
- YouTube (3 of 6 Phase 7 platforms) complete. 36 of 47 tables now
  shipped. Next: DV360.

## 2026-08-13 — Phase 7: build + validate DV360 (4 of 6 paid-media platforms)

- `generator/build_dv360_insertion_orders.py` -- 5 evergreen IOs (one per
  objective, all always-on -- same reasoning as Search's brand-term
  defense: a programmatic reach/awareness buy is a continuous line item on
  this platform, not a flighted study). The brand_lift IO uses
  PERFORMANCE_GOAL_TYPE_VIEWABLE_CPM, DV360's real awareness-oriented goal
  type.
- `generator/build_dv360_line_items.py` -- 6 line items, same
  targeting_segment_id split as every other platform (2 retargeting line
  items, 1 lookalike). The brand_lift IO's line item is VIDEO type; every
  other IO's stays DISPLAY.
- `generator/build_dv360_performance_daily.py` -- 25,776 rows. This is the
  table schema_reference.md calls out as genuinely different-shaped: real
  DV360 buys run across many open-web exchanges in real time, so each
  (line_item_id, date) fragments into 1-7 (exchange, environment) rows
  here instead of the single row per entity/day every other platform
  ships -- 5 exchanges (Google Ad Manager, AppNexus, OpenX, PubMatic,
  Index Exchange) x up to 4 environments (WEB_OPTIMIZED,
  WEB_NOT_OPTIMIZED, APP, and CONNECTED_TV -- CTV inventory reachable
  ONLY by the video/brand_lift line item, the platform's real
  differentiator vs. the other 5). Same seasonality-calendar x
  channel-mix-schedule spend driver as every other platform, via
  paid_media_common.py, at DV360's own ~7.5% average channel share.
- **No bugs found this round** -- first pass landed cleanly: total spend
  $132,525 matched the hand-computed expectation from the seasonality
  formula within the usual noise/pause tolerance (no cents/units error
  this time), and self-attributed conversions landed at 0.38x actual real
  purchases -- appropriately LOWER than every other platform's ratio so
  far, which is realistic (open-web display converts and self-attributes
  at a lower rate than search/social), not something that needed
  correcting.
- Validation: `validate_dv360_insertion_orders.py` 12/12,
  `validate_dv360_line_items.py` 12/12,
  `validate_dv360_performance_daily.py` **16/16 (central checks: the
  (line_item_id, date, exchange, environment) grain is unique -- the
  genuinely finer grain vs. every other platform's (entity, date) grain --
  CONNECTED_TV appears ONLY on the video line item, and the weekly
  spend-vs-web_sessions correlation, r=0.572 across 156 weeks)**. **40/40
  checks passed across all 3 DV360 tables, all on the first run.**
- DV360 (4 of 6 Phase 7 platforms) complete. 39 of 47 tables now shipped.
  Next: Snap.

## 2026-08-13 — Phase 7: build + validate Snap (5 of 6 paid-media platforms)

- `generator/build_snap_campaigns.py` -- 7 campaigns, same 4-evergreen +
  3-flighted-brand_lift structure as Meta/YouTube. Flight budgets
  ($900-1,100 lifetime, spread over each 18-day BFCM flight) were
  calibrated UP FRONT this time to the same ~1.2x-of-evergreen-baseline
  proportion Meta's flights land at, applying the lesson from YouTube's
  build (where copying dollar figures across channels without rescaling
  for a smaller channel share caused a real correlation-check failure).
- `generator/build_snap_ad_squads.py` -- 8 ad squads. Snap's real API
  genuinely has an explicit Ad Squad object (unlike Meta, where the
  ad-set-level fields had to live on meta_ads.csv itself) -- so
  targeting_segment_id lives on its own dedicated table here, the same 2
  retargeting / 1 lookalike / rest-broad split as every other platform.
- `generator/build_snap_ads.py` -- 10 ads, pure creative-level entity
  (single_image/video/collection ad_type) with no targeting of its own.
- `generator/build_snap_stats_daily.py` -- 7,407 rows. Spend reported in
  Snap's own micro-currency unit (schema_reference.md's specific callout
  for this table); "swipes" is Snap's click-equivalent (swipe-up rate),
  and video_views is reported on every row since Snap ad units are
  video-forward by default.
- **No bugs found this round** -- the up-front budget calibration worked:
  total spend $115,095 matched the hand-computed seasonality-formula
  expectation (~$116,700 after typical pause-day loss) on the first
  build, and self-attributed conversions landed at 0.63x actual real
  purchases, comfortably inside the believable range.
- Validation: `validate_snap_campaigns.py` 14/14,
  `validate_snap_ad_squads.py` 11/11, `validate_snap_ads.py` 9/9,
  `validate_snap_stats_daily.py` **13/13 (incl. the weekly spend-vs-
  web_sessions correlation, r=0.429 across 156 weeks -- Snap's own ~6.5%
  average channel share is the smallest of the 6 platforms, so a tighter-
  but-still-passing correlation than Meta's is expected, not a red flag)**.
  **47/47 checks passed across all 4 Snap tables, all on the first run.**
- Snap (5 of 6 Phase 7 platforms) complete. 43 of 47 tables now shipped.
  Next and last: TikTok.

## 2026-08-13 — Phase 7: build + validate TikTok (6 of 6) — PROJECT COMPLETE (47/47 tables)

- `generator/build_tiktok_campaigns.py` -- 7 campaigns, same 4-evergreen +
  3-flighted-brand_lift structure as Meta/YouTube/Snap. Flight budgets
  ($2,300-2,700 lifetime) calibrated up front to TikTok's own ~17.5%
  average channel share (2nd-largest of the 6 platforms) using the same
  proportion-of-evergreen-baseline approach validated on Snap.
- `generator/build_tiktok_adgroups.py` -- 8 ad groups. Real TikTok
  hierarchy is Campaign > Ad Group > Ad, structurally identical in shape
  to Snap's Campaign > Ad Squad > Ad -- so, like Snap, TikTok gets its own
  explicit targeting-level table rather than folding targeting into the
  creative table the way Meta does. Same 2 retargeting / 1 lookalike /
  rest-broad split as every other platform.
- `generator/build_tiktok_ads.py` -- 10 ads, pure creative-level entity
  (SINGLE_VIDEO/SPARK_AD/COLLECTION formats).
- `generator/build_tiktok_reports_daily.py` -- 7,416 rows. TikTok ad units
  are always video, so every row reports a high video-view share of
  impressions (>=50%), unlike Snap's mixed image/video/collection
  inventory.
- **No bugs found this round** -- the calibration-up-front discipline
  established after YouTube held: total spend $334,173 matched the
  hand-verified deterministic seasonality-formula total ($343,045 raw,
  ~$336,500 after typical pause/objective-loss) within normal noise, and
  self-attributed conversions landed at 2.69x actual real purchases --
  the higher end of the range but still within the same generous band
  used for YouTube (TikTok being the 2nd-highest-spend platform after
  Meta makes a higher absolute over-attribution volume expected, not
  suspicious).
- Validation: `validate_tiktok_campaigns.py` 13/13,
  `validate_tiktok_adgroups.py` 11/11, `validate_tiktok_ads.py` 8/8,
  `validate_tiktok_reports_daily.py` **14/14 (incl. the weekly
  spend-vs-web_sessions correlation, r=0.858 across 156 weeks -- the
  strongest of any platform's correlation check this phase, consistent
  with TikTok's large, stable channel share)**. **46/46 checks passed
  across all 4 TikTok tables, all on the first run.**
- **TikTok (6 of 6 Phase 7 platforms) complete. Phase 7 (all 22
  paid-media tables across 6 platforms) complete. All 47 of 47 tables in
  the Kinetic dataset are now built, validated, and shipped.**
- **Final full-suite validation**: re-ran all 47 tables' validators
  end-to-end in one pass after TikTok shipped, to confirm nothing had
  regressed across the whole project. **All 47 validators passed, 720
  checks total, zero failures.** This is the project's closing
  confirmation that the single shared master-timeline design (Phase 0)
  held its promise: every one of the 47 tables, built across 7 phases and
  many sessions, remains mutually consistent by construction -- no
  cross-table impossible scenarios anywhere in the dataset.

## 2026-08-13 — Post-completion: cross-dataset alignment audit (7 checks)

- New script `generator/audit_cross_dataset_alignment.py` -- **not** part
  of the standard build/validate pipeline (it doesn't ship a table). Its
  job is different from the 47 per-table validators: it checks whether
  AGGREGATE signals across every table agree with each other and with the
  shared seasonality calendar/channel-mix schedule, using correlation,
  growth-ratio, and volatility comparisons rather than exact-count
  reconciliation. Run standalone: `python3 audit_cross_dataset_alignment.py`.
- **Check 1 (aggregate spend vs. demand)**: PASS. Total weekly ad spend
  across all 6 platforms correlates strongly with weekly web_sessions,
  signups, orders, and revenue, and tracks the seasonality multiplier
  directly.
- **Check 2 (channel mix consistency)**: PASS. Actual weekly spend share
  per platform tracks `_sim_channel_mix_schedule.csv`'s intended mix,
  both per-platform and project-wide.
- **Check 3 (calendar-anchored events)**: PASS with a noted, non-bug
  finding -- BFCM brand_lift flights ran in all 3 Novembers
  (2023/2024/2025), but `discount_codes.csv` only has a matching holiday
  code + Braze "Seasonal Sale Promo" send for 2024. 2023 and Nov-2025
  brand-awareness campaigns ran with no accompanying promo mechanism.
  Left as-is (documented, not a data error) pending user direction.
- **Check 4 (long-run growth trend)**: PASS. Business volume shows the
  ~2.4x growth baked into the seasonality calendar; marketing efficiency
  (spend/signup) stays stable across quarters.
- **Check 5 (renewal/lag structure)**: PASS with a noted, non-bug finding
  -- renewal invoice volume does NOT show lower detrended volatility than
  fresh subscription starts, contrary to the initial hypothesis.
  Explainable by short average subscriber tenure and only 3 years of
  history limiting cohort-blending depth, plus annual-billing
  subscribers echoing their exact origin week a year later. Not a bug.
- **Check 6 (day-of-week / hour-of-day)**: **found and fixed a real
  issue.** Day-of-week is confirmed uniform everywhere (no table was
  ever designed with day-of-week weighting -- correct). Hour-of-day
  surfaced that all 38 `merch_to_sub_trigger` Braze email sends landed
  at exactly midnight (00:00:00) -- that one trigger type's code path in
  `build_braze_email_events.py` never called the `_random_time_of_day()`
  helper every other trigger type uses, so its sends inherited a bare
  date (implicit midnight) instead of a randomized business-hours time.
  **Fixed**: `merch_to_sub_trigger` now draws a random 6am-9pm send time
  like `trial_started`/`trial_ending`/`reactivation` do. Rebuilt
  `data/braze_email_events.csv` (26,335 rows, up from 26,328 -- the fix
  adds 2 extra `rng` draws per merch_to_sub_trigger row, which shifts the
  shared RNG stream for every send generated afterward, so the funnel's
  downstream open/click/bounce/unsubscribe outcomes differ slightly on a
  handful of rows even though the underlying populations and rates are
  unchanged). Re-ran `validate_braze_email_events.py`: **13/13 passed.**
  Confirmed web_sessions' own hour-of-day weighting (7am-11pm, 98.6% of
  sessions) is correct-by-design, not a gap.
- **Check 7 (timezone/precision sweep)**: PASS. Swept all 47 tables'
  49 datetime/date-only columns (after fixing the sweep's own
  timestamp-sniffing heuristic, which initially false-flagged numeric
  and text columns like phone numbers and state codes) -- zero stray
  timezone suffixes, zero sub-second fractions, zero mixed date/datetime
  formatting within any column, across the entire dataset.
- **Net result**: 6 of 7 checks passed clean; 1 check (day-of-week/
  hour-of-day) caught a real, fixed bug; 2 checks (3 and 5) surfaced
  genuine, explainable characteristics worth keeping visible to the user
  rather than silently accepting.

## 2026-08-13 — Next stage: warehouse loading tooling (MotherDuck)

- New `warehouse/load_to_motherduck.py` -- the dataset's first step
  outside the 47-table build/validate pipeline, per the project's
  original stated destination (`README.md`: raw data -> data platform ->
  semantic layer/canonical metrics -> AI agents). Loads all 47 CSVs into
  a free MotherDuck (hosted DuckDB) database, one table per CSV, with a
  per-table row-count verification (MotherDuck vs. source CSV) printed
  after the load.
- Chosen over a Snowflake trial for this stage because Snowflake's free
  trial is time-boxed (30 days / $400 credit, then the account is
  suspended), while MotherDuck's free "Lite" tier is permanent and
  comfortably covers this dataset's size (41MB / ~401K rows total vs.
  MotherDuck's 10GB free storage limit). Plan is to migrate to Snowflake
  later once the MotherDuck setup is solid, for the platform experience.
- Must be run on the user's own machine, not inside the Cowork cloud
  sandbox -- confirmed the sandbox's network allowlist blocks both
  pypi.org (so `duckdb` can't be pip-installed here) and motherduck.com
  directly, so this stage is intentionally handed off as a script + step-
  by-step instructions rather than executed in-session.

## 2026-08-13 — MotherDuck token handling: gitignored .env, not synced

- User provided a live MotherDuck read/write access token in chat.
  Deliberately did **not** write it into any git-tracked or Mac-synced
  project file -- this project's git history gets committed and the
  whole folder gets synced to iCloud on every change, and a credential
  baked into either would be effectively permanent/hard to revoke even
  after deletion (recoverable from git history) and unnecessarily
  exposed (iCloud sync). It also isn't needed there: the loader script
  only runs on the user's own machine, never inside the Cowork cloud
  sandbox (confirmed last entry -- sandbox has no route to
  motherduck.com).
- Added `.env` / `*.env` / `warehouse/.env` to `.gitignore`.
- `warehouse/load_to_motherduck.py` now optionally auto-loads
  `warehouse/.env` (a tiny manual parser, no new dependency) if present,
  falling back to the `motherduck_token` shell env var either way --
  explicit `export` always wins over the file. Stored the token in
  `warehouse/.env` inside this session's own (ephemeral, non-synced)
  workspace only, for reference during this session.
- **Not** added to `File_Manifest.xlsx` row content or synced to the
  user's Mac folder, by design -- only the (secret-free) `.gitignore`
  and script changes were. Advised the user to regenerate the token in
  MotherDuck's settings since it was pasted into a chat transcript, and
  to set it directly via `export motherduck_token=...` on their own
  machine (or their own local `warehouse/.env`, kept off git) as the
  actual long-term home for it.

## 2026-08-13 — Fix: load_to_motherduck.py couldn't create a new database

- First real run on the user's machine failed: `duckdb.connect("md:kinetic")`
  threw `Failed to attach 'kinetic': no database/share named 'kinetic'
  found`. `md:<name>` attaches to an EXISTING MotherDuck database -- it
  doesn't create one, which the script had wrongly assumed.
- **Fixed**: connect bare (`md:`, no database name) first, then
  `CREATE DATABASE IF NOT EXISTS kinetic` and `USE kinetic` via SQL
  before creating any tables. Idempotent -- safe to re-run on a later
  session once the database already exists.
- **Confirmed working**: user ran the fixed script against their own
  MotherDuck account -- all 47 tables loaded, all 47 row counts matched
  their source CSVs exactly. First successful end-to-end migration of
  the dataset out of flat files into a queryable warehouse.

## 2026-08-13 — First analysis queries: warehouse/analysis_queries.sql

- 6 starter SQL queries against the `kinetic` MotherDuck database:
  monthly paid media spend by partner, directly attributed revenue by
  paid/owned channel, active subscribers by month, non-subscription
  revenue by month, monthly churn rate, and top 5 grossing products per
  year.
- The paid-vs-owned attribution query (#2) surfaces a real methodology
  split inherent to this dataset's design (no user-level ad-platform
  joins, per `docs/schema_reference.md`): storefront orders attribute
  via session-level UTM (order -> purchase web_event -> session ->
  utm_source, true last-click), while subscription/invoice revenue has
  no session to join through and instead uses `customers.signup_source`
  (first-touch) applied to every invoice for that customer. Both
  methods are used and documented in-line rather than picking one
  silently. ~0.5% of storefront orders (17 of 3,650) have no matching
  purchase event and are bucketed as `untracked` rather than folded into
  `owned`.
- The active-subscribers and churn-rate queries share an "actually
  converted to paid" definition: a subscription canceled during its own
  trial (`canceled_at <= trial_end`) never became a paying subscriber
  and is excluded from both active counts and churn counts, regardless
  of the `status` column.
- Validated all 6 queries' logic against the source CSVs in pandas
  before handing them off (active-subscriber counts grow plausibly from
  0 to 100 over the 3-year window; monthly churn lands in a believable
  single-digit-percent range; spend/revenue/top-product numbers are
  sane) -- couldn't execute the actual SQL/MotherDuck connection from
  this cloud sandbox (no network route to motherduck.com), so this was
  the available substitute for the project's usual "validate before
  shipping" discipline.

## 2026-08-13 — First chart: warehouse/query1_paid_media_spend.html

- User ran Query 1 in MotherDuck and pasted the actual output back;
  visualized it as a self-contained interactive HTML chart (multi-line,
  6 partners x 36 months) using the dataviz skill's procedure: form
  (multi-line for "tell distinct series apart") -> categorical palette
  (validated via the skill's own script, both light and dark surfaces,
  before use) -> mark specs -> hover crosshair/tooltip -> accessibility
  pass (legend + table view, since 3 of the 6 hues fall under 3:1 text
  contrast on the light surface by the palette's own documented design).
- Stat tiles up top (total spend, latest month, peak month, average
  month) computed directly from the pasted data, cross-checked by hand:
  $1.5M total matches the cross-dataset audit's Check 1 total
  ($1,532,136.55) almost exactly; peak month Jan 2026 ($86.1K) lines up
  with the New Year's-resolution acquisition surge documented in
  `docs/business_context.md`'s seasonality calendar.
- Rendered and screenshotted in a headless browser (light, hover
  tooltip, dark mode, table view) before delivery to catch layout/JS
  issues -- couldn't rely on "looks right in the editor" alone.
- Treated as a one-off (SendUserFile only, not persisted as a Cowork
  artifact) since it visualizes one specific pasted query result, not a
  dashboard the user asked to keep returning to.

## 2026-08-14 — Live MotherDuck Dive: all 6 queries as one dashboard

- Now that the `mcp__MotherDuck__*` tools are connected directly in this
  session, I queried the live `kinetic` database myself (no more
  copy/paste needed) and built a MotherDuck "Dive" -- a saved,
  interactive dashboard app that re-runs the actual SQL against the
  real database every time it's opened, rather than a static image
  built from one-time results.
- Covers all 6 requested queries in one page: paid media spend by
  partner, attributed revenue by paid/owned channel, active
  subscribers by month, non-subscription revenue by month, churn rate
  by month, and top 5 grossing products per year -- plus a KPI row
  (total paid media spend, storefront revenue, total orders, current
  active subscribers).
- Followed the MotherDuck MCP server's own required workflow: called
  `get_dive_guide` before writing any chart code, used the platform's
  house visual style (its own palette/spacing/KPI-row conventions,
  distinct from the general `dataviz` skill used for the earlier
  one-off HTML chart), converted every numeric value defensively
  (DuckDB BIGINT/DECIMAL values arrive as non-primitive objects, not
  plain JS numbers), and filled missing months with a generated date
  spine so gaps don't silently disappear from the charts.
- Live-validated all 6 queries via direct MCP calls against the real
  database before building the dashboard -- results matched the
  earlier pandas/paste validation.
- Saved via `save_dive`, then re-opened via `view_dive` to confirm the
  saved source matches exactly. Local source-of-truth copy kept at
  `warehouse/kinetic_dive.tsx` per the project's sync discipline, since
  the dashboard itself lives on MotherDuck's servers, not in this
  folder.
- `kinetic` database is not yet shared with Ben's MotherDuck
  organization -- asked whether to share it so others could view the
  Dive; not yet actioned pending his answer.

## 2026-08-14 — Dive v2: 8 persona-specific user stories added (CEO/CMO/CFO/PMM)

- User asked for 3 user-story dashboard requests per persona (CEO, CMO, CFO,
  Performance Marketing Manager -- 8 stories total) built directly into the
  live Dive, not just described. Explored the schema for every table
  involved (customers, subscriptions, invoices, orders, discount_codes,
  payments, refunds, web_sessions, web_events, app_sessions, all 6 ad
  platforms' campaign + performance tables) and live-validated each new
  query against the real kinetic database before writing any chart code.
- Restructured the Dive into 5 tabs (Overview / CEO / CMO / CFO /
  Performance Marketing) using `useDiveState` so the active tab is part of
  the shareable link, rather than one long page of 14+ sections.
- CEO: revenue growth rate + net-new-vs-churned paying subscribers + CAC
  payback trend; revenue mix across subscription/course/merch.
- CMO: acquisition funnel (sessions -> trial starts -> paid conversions) by
  channel; retention and app engagement by original acquisition channel.
- CFO: CAC and LTV:CAC by acquisition cohort; discount code cost + failed
  payment recovery rate + a net-margin proxy.
- Performance Marketing: campaign-level spend and platform-self-reported
  efficiency across all 38 real campaigns (sorted worst-CAC-first so an
  underperformer surfaces immediately); CTR/CVR benchmarked by platform and
  ad format.
- Three modeling limits surfaced and documented directly in the dashboard
  copy rather than silently glossed over: (1) this dataset has no
  per-product cost data, so "net margin proxy" (gross revenue minus
  discounts minus refunds) is shown instead of true gross margin; (2)
  failed-payment recovery rate is 100% by construction, since the dataset
  only ships orders that eventually completed -- shown as a data-integrity
  check, not a leaky-bucket signal; (3) there is no join key tying an
  individual ad-platform campaign to a specific site session (utm_campaign
  is an independently-generated theme tag, confirmed by reading
  generator/build_web_sessions.py), so campaign-level efficiency uses each
  platform's own self-reported conversions rather than fabricating a false
  attribution join -- called out explicitly in the dashboard text.
- Updated the same saved Dive (dive_id 58909b4e-..., now version 2) via
  `update_dive`, then re-verified with `view_dive`. Local source-of-truth
  copy at `warehouse/kinetic_dive.tsx` updated to match exactly and synced.

## 2026-09-28 — Recovered git history pushed to GitHub; audit gap closed; dbt semantic layer started

- Six weeks after the last session, the git history (52 commits, lost when the
  prior cloud sandbox that held them was recycled) was recovered from a backup
  tarball on Ben's Mac, verified intact (`git log` still showed all 52 commits,
  clean working tree), and pushed to `github.com/bencool85/kinetic-data-project`.
  All 595 objects transferred; the repo's `master` branch now matches this
  project's full history.
- Discovered along the way that this project's git working copy can no longer
  live inside the iCloud-synced `Data_Engineering_Project_July2026` folder --
  iCloud's "cloud-only" placeholder files can't be read through the automation
  bridge used to drive the Mac (reads fail with a filesystem deadlock error),
  and git's own internal write pattern (rapid small file changes on every
  commit) doesn't mix well with iCloud sync regardless. The working git clone
  now lives at `~/Documents/kinetic-project` -- a plain local, non-iCloud
  folder -- with GitHub as the actual "access from anywhere" cloud copy. The
  iCloud folder keeps its original job: a synced, human-browsable mirror of
  the current files via `File_Manifest.xlsx`, not a git-tracked directory.
- Closed the one open item from the cross-dataset alignment audit: the
  brand_lift/holiday-discount-code asymmetry across the 3 Novembers (2023/
  2024/2025) is being kept as-is, confirmed intentional realism rather than a
  gap to fix. See `docs/cross_dataset_alignment_audit.md` for the resolution
  note.
- README updated with the project's actual current status (all 47 tables
  built + validated, live in MotherDuck) and a direct link to the live Dive
  dashboard.
- Started a `dbt/` project -- the "semantic layer" step from this project's
  original stated roadmap (raw data -> data platform -> semantic layer ->
  AI agents). Scaffolded staging/intermediate/marts folder structure and
  `dbt_project.yml`; first staging models built and validated against the
  live `kinetic` database next. This is being built incrementally, phase by
  phase (same discipline as the original 47-table build), not all at once.

## 2026-09-28 — dbt Phase 3: storefront revenue

- Staging models for the storefront entities: `orders`, `order_line_items`,
  `payments`, `refunds`, `discount_codes`.
- New intermediate model `int_orders_refunded`: total successfully-refunded
  amount per order (only `status = 'succeeded'` refunds count -- a
  requested-but-failed refund shouldn't reduce reported revenue).
- New mart `mart_storefront_revenue_monthly`: non-subscription (course +
  merch) gross/net revenue, AOV, guest-checkout share, discount-usage
  share, and refund rate by month. Net revenue is gross minus successful
  refunds only -- explicitly documented as not a true gross margin figure,
  since this dataset has no COGS data (same caveat already on the
  MotherDuck Dive's CFO tab).
- Validated against a hand-run equivalent query on the live `kinetic`
  database before writing any dbt SQL: 2026-07 showed 246 orders,
  $13,843.71 gross revenue, $56.28 AOV, 13.0% guest orders, 19.5% with a
  discount applied, 4.5% of orders refunded ($649.59).

## 2026-09-29 — Adopted the Data-to-Agents Playbook; Phase 2 sub-batch 1 (Customer 360 staging)

- Wrote a reusable consulting framework, the "Data-to-Agents Playbook"
  (published as a separate page, not in this repo): 9 phases from discovery
  through staging, intermediate, marts, documentation, a dynamic semantic
  layer, Skills, and agents. Kinetic now follows it phase by phase, finishing
  each phase across all tables before starting the next.
- Phase 2 (staging) is being completed in 9 sub-batches, grouped in the same
  dependency order as the original 47-table build. Sub-batch 1, Customer 360:
  `customer_addresses`, `devices`, `identity_map`, `segments`,
  `customer_segment_membership`, `subscription_events`. 16 of 47 raw tables
  now staged.
- Since `dbt test` can't run yet, every test was verified by hand against the
  live database first: all 6 primary keys unique and non-null; every foreign
  key resolves (addresses/devices/identity_map/membership/subscription_events
  -> customers, membership -> segments, subscription_events -> subscriptions,
  old/new plan -> subscription_plans, identity_map.anonymous_id -> devices).
- `devices.customer_id` is null for 17,050 of 18,042 rows (anonymous devices
  that never resolved to a customer). That's by design, so that column gets a
  relationships test but deliberately no not_null test.

## 2026-09-29 — Phase 2 sub-batch 2: web/app engagement staging

- Staging models + tests for `web_sessions`, `web_events`, `app_sessions`,
  `app_events`. 20 of 47 raw tables now staged.
- Hand-verified against the live database before writing the tests:
  - Primary keys unique and non-null in all 4 tables (30,285 web sessions,
    117,706 web events, 19,610 app sessions, 39,370 app events).
  - Every foreign key resolves: web/app events -> their sessions; sessions
    and events -> customers where filled in; web sessions/events ->
    devices via anonymous_id; app sessions -> devices via device_id; web
    events -> products and orders where filled in.
- `customer_id` is null on 23,809 web sessions (~79%) and 90,603 web events:
  visitors who weren't known customers yet. Expected by design, so those
  columns get relationships tests but no not_null test. App sessions and
  events always have a customer, so there they do get not_null.

## 2026-09-29 — Phase 2 sub-batch 3: email/push (Braze) staging

- Staging models + tests for `braze_email_campaigns`, `braze_email_events`,
  `braze_push_campaigns`, `braze_push_events`. 24 of 47 raw tables staged.
- Two light cleanups, both allowed in staging because they don't change
  meaning: Braze's `external_user_id` is renamed to `customer_id` (it is
  Kinetic's customer ID), and a short `event_name` (send/open/click/bounce/
  unsubscribe) sits next to Braze's raw `event_type`
  (users.messages.email.Open etc.). Checked on live data that event_name
  yields exactly those 5 values in both tables.
- Hand-verified before writing tests: all 4 primary keys unique and
  non-null (9 email campaigns, 26,335 email events, 7 push campaigns,
  9,897 push events); every event's campaign exists; every filled-in
  customer exists; every push device exists and belongs to the same
  customer the push was sent to.
- 2,187 email events have no customer_id. All of them are Order
  Confirmation emails to guest checkouts, and every address matches a
  guest order's email. Expected, so no not_null test on that column.
- Noted for Phase 3 (intermediate): 28 of those guest-checkout emails
  match an existing customer's email address -- people who checked out as
  a guest despite having an account, or created one later. Any "customer
  view" of email engagement or orders will need to decide whether to stitch
  those together by email address.

## 2026-09-29 — Phase 2 sub-batch 4: paid media, Meta staging

- Staging models + tests for `meta_campaigns`, `meta_ads`,
  `meta_ad_insights_daily`, `meta_ad_actions_daily`. 28 of 47 raw tables
  staged.
- Units made explicit in column names, after confirming them in the
  generator code (`build_meta_campaigns.py`, `build_meta_ad_insights_daily.py`):
  - Budgets are stored in cents (Meta API convention). Staging keeps the raw
    `*_budget_cents` and adds `*_budget_usd`. In dollars: always-on
    campaigns run $60-$140/day; brand-lift flights $3,500-$4,000 lifetime.
    Cross-check: total Meta spend is $429,401, in line with ~$400/day of
    always-on budget over the 3 years plus the 3 flights.
  - `ctr` is a fraction (0.017 = 1.7%), not a percentage -- renamed
    `ctr_fraction`. Spend, CPM and CPC get a `_usd` suffix.
- The two daily tables have no single ID column (a row is ad + date, or
  ad + date + action type), so staging builds a combined key (`ad_day_id`,
  `ad_day_action_id`) and tests it for uniqueness. Verified on live data
  with the exact same expressions: zero duplicates; every action row has
  a matching insights row.
- Also verified: all IDs unique and non-null (7 campaigns, 10 ads, 7,396
  ad-days, 35,504 ad-day-actions); every ad's campaign exists; every
  targeting segment exists; the campaign_id on each daily row matches its
  ad's campaign.

## 2026-09-29 — Phase 2 sub-batch 5: paid media, Google Search staging

- Staging models + tests for `google_search_campaigns`,
  `google_search_ad_groups`, `google_search_performance_daily`,
  `google_search_keyword_performance_daily`. 32 of 47 raw tables staged.
- Renamed a dangerous column: `google_search_campaigns.customer_id` is the
  Google Ads *account* number (123-456-7890), not a Kinetic customer. It is
  now `google_ads_account_id`, so nobody joins it to `customers`.
- Units confirmed in the generator code: cost, CPC and budgets are in micros
  (millionths of a dollar, Google Ads convention); staging adds `_usd`
  versions. Daily budgets are $35-$120 per campaign. `ctr` is a fraction.
  `conversions_value` is already dollars. Conversions can be fractional.
- Two columns are entirely empty and had loaded as text: `end_date` (no
  campaign has a scheduled end) and `cpc_bid_micros` (automated bidding, so
  no manual bid). Staging casts them back to a date and a number.
- `google_search_performance_daily` is built by summing the keyword table
  (confirmed in `build_google_search_performance_daily.py`). Verified on
  live data that cost, clicks, impressions and conversions match on every
  one of the 8,751 ad-group-days (total cost $350,535.12 in both). The
  models are documented as "use one or the other, never add them together".
- Also verified: all IDs unique and non-null (5 campaigns, 8 ad groups,
  8,751 ad-group-days, 19,932 keyword-days, 19 keywords each in exactly one
  ad group); every ad group's campaign and targeting segment exists; the
  campaign_id on every daily row matches its ad group's campaign.

## 2026-09-29 — Phase 2 sub-batch 6: paid media, YouTube staging

- Staging models + tests for `youtube_campaigns`, `youtube_ad_groups`,
  `youtube_performance_daily`. 35 of 47 raw tables staged.
- Same Google Ads conventions as Google Search (confirmed in the generator
  code): `customer_id` is the Google Ads account number (the same account,
  123-456-7890) and is renamed `google_ads_account_id`; budgets, cost and
  cost-per-view are in micros and get `_usd` versions. Budgets arrived as
  decimals; verified the cast to whole micros loses nothing.
- In dollars: always-on campaigns $15-$45/day; holiday brand-lift flights
  $2,500 / $2,700 / $2,900 lifetime (2023 / 2024 / 2025). Total YouTube
  spend $170,406.94.
- `video_view_rate` is a fraction (0.284 = 28.4% of impressions became
  views), renamed `video_view_rate_fraction`. Verified it equals views /
  impressions, and that average CPV equals cost / views.
- Also verified: all IDs unique and non-null (7 campaigns, 9 ad groups,
  6,394 ad-group-days, combined key included); every ad group's campaign
  and targeting segment exists; each daily row's campaign matches its ad
  group's campaign.

## 2026-09-29 — Phase 2 sub-batch 7: paid media, DV360 staging (+ a budget problem found)

- Staging models + tests for `dv360_insertion_orders`, `dv360_line_items`,
  `dv360_performance_daily`. 38 of 47 raw tables staged.
- `dv360_performance_daily` is one row per line item, per day, per ad
  exchange, per environment (web / app / connected TV): 25,776 rows
  covering 6,312 line-item-days. Staging builds a combined key
  (`line_item_day_slice_id`); verified zero duplicates. Also verified: all
  IDs unique and non-null (5 insertion orders, 6 line items); every line
  item's insertion order and targeting segment exists; each daily row's
  insertion order matches its line item; display line items never appear
  on connected TV (only video can); conversion value averages $90 per
  conversion, so it's already dollars. Total DV360 spend $132,525.13.
- `budget_micros` is a MONTHLY budget (30x a daily figure, confirmed in
  `build_dv360_insertion_orders.py`), so staging names it
  `monthly_budget_usd` ($300-$900 per insertion order).

### Problem found: spend exceeds stored budgets on 4 platforms

- DV360 spent more than its stored monthly budget in 124 of 180
  insertion-order-months, up to 2.41x. Real DV360 pacing stops at the
  budget, so as stored this is an impossible scenario.
- Cause: every campaign's budget is set once, at launch, and never
  changes, while spend follows the business's growth curve
  (`GROWTH_END_MULTIPLIER = 2.4`). Spend averages 84% of budget in 2023 and
  150% in 2026.
- Checked the other platforms with daily budgets, against each platform's
  real monthly limit (30.4x the daily budget):
  | Platform | Campaign-months over the limit | Worst month |
  |---|---|---|
  | Meta | 48 of 144 | 1.80x |
  | Google Search | 53 of 180 | 1.93x |
  | YouTube | 97 of 144 | 3.39x |
  | DV360 (monthly budget) | 124 of 180 | 2.41x |
- The holiday brand-lift flights (lifetime budgets) are fine: within 5% of
  budget; two Meta flights over by 1-2% ($60, $49), within normal
  platform tolerance.
- **Correction:** the Meta entry above says total Meta spend is "in line
  with ~$400/day of always-on budget". That was a rough whole-period
  comparison and is misleading; month by month, Meta runs over its daily
  budgets in the later months, as shown here.
- Why it slipped through: the original per-table validators only checked
  that budgets exist; none compared budgets to spend.
- Impact: no dashboard or analysis query uses budget columns, so no
  reported number is wrong today. It would matter for any future "spend
  vs budget" or pacing analysis. Snap and TikTok still to check when
  they're staged. Fix pending Ben's decision; staging does not alter data.

## 2026-09-29 — Fixed: ad budgets are now each campaign's current budget

- Ben chose to store each campaign's current budget -- the only budget a
  real ad platform keeps on the campaign object. Earlier months simply ran
  under it (budgets get raised as the business grows).
- Extended the check to Snap and TikTok before fixing, since they weren't
  staged yet. They were the worst: e.g. TikTok prospecting stored $16/day
  against a busiest week averaging $309/day (~20x).
- Standard used, from mainstream ad-platform rules: every calendar week
  averages at or under the daily budget (Meta's weekly cap; stricter than
  Google's 30.4x monthly cap), no single day above 1.75x (Meta's daily
  allowance; Google allows 2x), and DV360's monthly budget covers its
  highest month. Rounded up to the nearest $5 (under $100) or $10.
- Changed `params.py` (the 6 evergreen budget dicts, plus a comment
  explaining the rule) and rebuilt only the 6 campaign tables. Diffed old
  vs new files: only the budget column changed, and only on the 26
  always-on campaigns; holiday flights and every other column identical.
  Spend is untouched -- the spend generators never read these budgets
  (confirmed in code), so no dashboard or analysis number changes.
- New daily budgets: Meta $140-$320, Google Search $75-$270, YouTube
  $65-$150, Snap $35-$85, TikTok $130-$310; DV360 monthly $750-$2,250.
- All 77 original validator checks on the 6 tables still pass.
- New Check 8 in `audit_cross_dataset_alignment.py`: spend vs budget for
  every campaign. Result after the fix: 0 of 3,297 campaign-weeks over,
  0 days over 1.75x, 0 of 180 DV360 months over (worst 0.99x).
- Applied the same 26 values to the live MotherDuck database (Ben
  approved the write; a first attempt errored on an integer overflow in my
  SQL and was rolled back automatically -- verified nothing had changed
  before retrying). Verified every budget value in all 6 MotherDuck tables
  matches the regenerated CSVs exactly.
- Check 8 also flagged 6 holiday flights that spent 0.7%-6.4% over their
  lifetime budgets ($430 total). Ben chose to cap flight spend at budget;
  that fix follows in the next entry.

## 2026-09-29 — Fixed: holiday flights capped at their lifetime budget

- Ben chose to cap flight spend at budget. 6 of 12 holiday brand-lift
  flights had overshot their lifetime budgets by 0.7%-6.4% ($430 total):
  Meta 2023/2024, Snap 2024, TikTok 2023/2024/2025. Cause: each flight
  day's spend is a random draw around budget / days, and nothing capped
  the total.
- New `cap_flight_at_budget()` in `paid_media_common.py`, wired into the
  Meta, Snap, TikTok and YouTube spend generators. If a flight's total
  lands over budget, its days are scaled down proportionally so it spends
  exactly the budget. Impressions/clicks etc. are rebuilt from the SAME
  random rates (the saved random-generator state is replayed on a
  throwaway copy), so the shared random stream -- and every other row in
  each table -- is untouched. Confirmed each flight has exactly one ad, so
  capping per ad equals capping per campaign.
- Rebuilt meta_ad_insights_daily, meta_ad_actions_daily, snap_stats_daily,
  tiktok_reports_daily, youtube_performance_daily. Diffed every row
  against the previous files: only the 5 overshooting flights' rows
  changed (38 Meta insights rows, their action rows, 19 Snap rows, 56
  TikTok rows); YouTube identical; nothing outside those flights moved.
  One Meta action row disappeared: on 2024-11-15 the trim took
  initiate_checkout from 1 to 0, and zero-count actions aren't emitted
  (same as Meta's API).
- Total ad spend across all 6 platforms: $1,532,136.55 -> $1,531,706.93
  (-$429.62, exactly the overshoot). Meta total is now $429,291.38 (the
  Meta staging entry above quoted $429,401.02 before this fix).
- All 69 validator checks on the 5 rebuilt tables pass. Audit checks 1
  and 3 re-run: spend-vs-demand correlations unchanged in substance (web
  sessions r=0.804, signups 0.659, orders 0.486, revenue 0.497); flight
  dates unchanged. Check 8 now requires flights to be at or under budget
  (was 1.05x) and passes: all 12 flights at or under.
- Applied to live MotherDuck (Ben approved): for each table, the 5 flights'
  old rows deleted and regenerated rows inserted in one transaction per
  table (271 rows total). Verified all 4 tables match the CSVs exactly:
  row counts plus exact whole-table totals of every numeric column. Also
  confirmed from MotherDuck that every flight is at or under budget.
- No dashboard logic changes; the Dive's paid-media spend totals drop by
  the $430 (under 0.03%).

## 2026-09-29 — Phase 2 sub-batch 8: paid media, Snap staging

- Staging models + tests for `snap_campaigns`, `snap_ad_squads`,
  `snap_ads`, `snap_stats_daily`. 42 of 47 raw tables staged.
- Snap vocabulary documented in the models: an "ad squad" is Snap's ad set
  / ad group level, and "swipes" are Snap's clicks (swipe-ups) -- there is
  no clicks column.
- Budgets and spend are in micros (Snap micro-currency); `_usd` versions
  added. Budgets are the current budgets set in the 2026-09-29 fix; checked
  the cast to whole micros loses nothing and every campaign has exactly one
  of daily / lifetime budget. `ad_account_id` renamed `snap_ad_account_id`.
- Hand-verified before writing tests: all IDs unique and non-null (7
  campaigns, 8 ad squads, 10 ads, 7,407 ad-days incl. the combined
  `ad_day_id` key); every link resolves through all four levels (campaign
  -> ad squad -> ad -> daily row), and each daily row's ad squad and
  campaign match its ad's; every targeting segment exists; swipes and
  video views never exceed impressions; conversion value averages $90.61,
  so it's dollars. Total Snap spend $115,034.09 (after the flight cap).

## 2026-09-29 — Phase 2 sub-batch 9: paid media, TikTok staging

- Staging models + tests for `tiktok_campaigns`, `tiktok_adgroups`,
  `tiktok_ads`, `tiktok_reports_daily`. 46 of 47 raw tables staged; all 6
  paid-media platforms done.
- TikTok keeps one `budget_micro` column plus a `budget_mode` flag (daily
  vs. total). Staging keeps both raw columns and adds `daily_budget_usd` /
  `lifetime_budget_usd`, so budgets line up with the other 5 platforms.
  Checked: 4 always-on campaigns get daily budgets ($130-$310), the 3
  holiday flights get lifetime budgets ($2,300 / $2,500 / $2,700).
- Units: spend and CPM in micros (`_usd` added); `ctr` is a fraction,
  renamed `ctr_fraction`. `advertiser_id` renamed `tiktok_advertiser_id`.
- Hand-verified before writing tests: all IDs unique and non-null (7
  campaigns, 8 ad groups, 10 ads, 7,416 ad-days incl. the combined
  `ad_day_id` key); every link resolves through all four levels and each
  daily row's ad group and campaign match its ad's; every targeting
  segment exists; clicks and video views never exceed impressions; CTR
  equals clicks / impressions and CPM equals spend / impressions x 1,000;
  conversion value averages $89.15, so it's dollars. Total TikTok spend
  $333,914.27 (after the flight cap).

## 2026-09-29 — Phase 2 sub-batch 10: product_variants staging (Phase 2 complete)

- Added `stg_kinetic__product_variants`, the last of the 47 raw tables. **All
  47 raw tables are now staged; Phase 2 is complete.**
- Renames: `option_value` -> `variant_option`, `price_adjustment` ->
  `price_adjustment_usd`, `created_at` -> `variant_created_at`.
- Hand-verified before writing tests: 21 variants, all `variant_id` and
  `sku` unique and non-null; every variant points at a real product (0
  orphans) and all 12 products have at least one; no negative price
  adjustments (all $0); every variant was created on or after its
  product's creation date; all 21 active.

## 2026-09-29 — Added HANDOFF.md

- New `HANDOFF.md` at the repo root: status, open decisions, decisions already made, what Ben already understands, per-session setup, and past pitfalls. Written so a new chat or project can start without this conversation.

## 2026-09-29 — Playbook is now the working plan

- Ben: work from the Data-to-Agents Playbook and update it as we go. Its
  section 13 (Applied to Kinetic) now shows Phase 2 done (47/47), the
  Phase 3 build order, and the 3 open decisions; republished to the same
  page. The local copy and the published page had drifted (42 vs 46 of 47
  staged); both now match.
- HANDOFF.md: added the rule to update section 13 at the end of every
  sub-batch.

## 2026-09-29 — Phase 3 sub-batch 1: int_customer_identity

- New `int_customer_identity`: one row per identifier (web `anonymous_id`
  or account email) with the customer it belongs to and how the link was
  made (`identity_map_signup`, `identity_map_login`, `account_email`).
  Downstream models join on `identifier_key`.
- Ben's decisions, written as a comment above the SQL:
  - Match guest emails to accounts by email, before or after signup.
    Affects 28 of 1,257 guest orders (10 placed before signup, 18 after)
    and the same 28 Braze guest addresses.
  - Back-fill: a visitor's earlier anonymous web sessions belong to the
    customer once identity_map links them. Affects 340 of 23,809
    anonymous sessions.
- Assumption (flagged to Ben): deleted accounts (11) are excluded, so no
  new activity attaches to them. No current links point at them, so it
  changes nothing today.
- Hand-verified on live data before writing the model: customer emails
  and guest emails are already lowercase/trimmed, none null; 860 emails
  for 860 customers; identity_map has 992 rows, 992 distinct anonymous
  IDs, no nulls, every customer real (849 customers; 143 of them also have
  a second "login" ID, which lives on devices, not web sessions); no web
  session's customer disagrees with identity_map; app sessions always
  carry customer_id, so nothing to back-fill there.
- Model output checked with equivalent SQL: 1,841 rows (992 anonymous IDs
  + 849 emails), 1,841 distinct keys, no nulls. Tests: unique/not_null on
  `identifier_key`, accepted values on type and method, relationships to
  customers.
- dbt/README.md and File_Manifest.xlsx updated; HANDOFF open decision 1
  (Braze stitching) marked resolved.

## 2026-09-29 — dbt install setup (first real run pending)

- Ben's call: install dbt now rather than at Phase 5, since Phase 2's exit
  test (staging tests pass in dbt) can't be met without it and 52 models
  have never been compiled.
- New `dbt/profiles.yml` (in the project, no secrets): `md:kinetic`,
  `schema: dbt_dev`. Combined with the folder schemas, dbt builds into
  `dbt_dev_staging`, `dbt_dev_intermediate`, `dbt_dev_marts`. Checked the
  live database first: only `main` exists (47 tables), so no collisions.
  Ben approved `dbt run` writing to these schemas.
- `dbt/README.md` setup rewritten: venv at `~/.dbt-venv`, then
  `dbt debug` / `dbt run` / `dbt test`.
- `.gitignore`: dbt `target/`, `logs/`, `dbt_packages/`, `.user.yml`.
- Playbook v1.1 (Ben approved): Phase 1 now requires dbt installed and one
  clean run. Kinetic Phase 2 status moved back to "in progress" until
  `dbt test` passes.
- HANDOFF: new pitfall (git lock files without delete permission) and the
  dbt_dev decision.

## 2026-09-29 — First real dbt run: staging builds; test syntax updated for dbt 1.10

- Ben installed dbt 1.10.23 + dbt-duckdb 1.10.0 (Python 3.9.6, venv
  ~/.dbt-venv). `dbt debug`: all checks passed.
- `dbt run --select staging` on Ben's Mac: PASS=47, ERROR=0, 22.7s. All
  47 views created in `dbt_dev_staging`.
- Checked from MotherDuck: each of the 47 views returns exactly the same
  row count as its raw table (401,182 rows in total), and `main` still has
  its 47 raw tables, untouched.
- dbt 1.10 warned 67 times (MissingArgumentsPropertyInGenericTestDeprecation):
  `relationships` and `accepted_values` tests must nest their settings
  under `arguments:`. Updated all 67 (64 staging, 3 intermediate);
  confirmed both YAML files parse and every such test now has only
  `arguments`. Warnings only, no logic change.

## 2026-09-29 — Phase 2 exit: staging tests pass in dbt

- `dbt test --select staging` on Ben's Mac: 206 tests, PASS=205, ERROR=1,
  12.7s. No deprecation warnings after the `arguments:` fix.
- All 205 staging tests pass. That meets the playbook's Phase 2 exit
  criterion, so **Phase 2 is complete**.
- The 1 error is not a data problem: `--select staging` also picked up the
  relationships test on `int_customer_identity` (it points at
  stg_kinetic__customers), and that model hasn't been built in dbt yet, so
  the table didn't exist ("Catalog Error"). It will run once the
  intermediate layer is built.

## 2026-09-29 — Intermediate layer built and tested in dbt

- `dbt build --select intermediate` on Ben's Mac: 3 models + 12 tests,
  PASS=15, ERROR=0, 13.0s. Views in `dbt_dev_intermediate`. The
  int_customer_identity relationships test that errored in the staging
  run now passes.
- Checked the dbt-built views from MotherDuck:
  - int_customer_identity: 1,841 rows (992 anonymous IDs); links 28 guest
    orders and back-fills 340 sessions -- same as the pre-build check.
  - int_subscription_paid_periods: 576 rows = 576 subscriptions. 374 have
    no paid start. Looked into it because 65% seemed high: all 374 were
    canceled during their trial, and none of them has a paid invoice. The
    other 202 = 199 with a paid invoice + 3 still trialing (their paid
    start is their trial end date). So the model is right; the synthetic
    data has a 65% trial-cancel rate.
  - int_orders_refunded: 159 orders = 159 orders with a succeeded refund
    in raw; $6,546.82 refunded in total.
- Marts: added a `unique` test on `year_month` to both marts, so their
  one-row-per-month grain is tested (playbook: test the grain).

## 2026-09-29 — Marts built and tested in dbt; MRR mart no longer invents future months

- `dbt build --select marts` on Ben's Mac: 2 models + 6 tests, PASS=8,
  10.4s. Tables in `dbt_dev_marts`. Every existing model has now been
  built and tested in dbt.
- Checked from MotherDuck: `mart_mrr_monthly` reproduces the 2026-09-28
  hand check exactly (2026-07: 90 subscribers / $2,133.07 MRR).
  `mart_storefront_revenue_monthly` covers 36 months (2023-08 to 2026-07);
  its order counts sum to 3,650 = every raw order.
- **Bug found and fixed (Ben's call):** the MRR mart's month series ran to
  `current_date`, but the data ends 2026-07-30. So 2026-08 and 2026-09
  were made up: no cancellations are recorded after the data ends, and 3
  still-trialing subscriptions counted as paying. MRR appeared to rise to
  $2,357.82 (101 subscribers). Now the series ends at the month of the
  latest subscription/invoice record, computed from the data, and each
  row carries a `data_through` date (2026-07-30 today) with a not_null
  test. Ran the new SQL against the dbt-built views: 35 months (2023-09 to
  2026-07), all 35 identical to the old rows; only the 2 invented months
  are gone. Needs `dbt build --select mart_mrr_monthly` on Ben's Mac to
  update the table.
- Ben rebuilt `mart_mrr_monthly` in dbt (model + 4 tests pass). Confirmed
  from MotherDuck: 35 months, last 2026-07, data_through 2026-07-30, July
  MRR $2,133.07.
- HANDOFF.md: added "Next step" (int_orders_net) for the next chat.

## 2026-09-30 — int_orders_net written and hand-verified (awaiting dbt build)

- New `int_orders_net` (one row per order): gross_usd (pre-discount
  subtotal), discount_usd (subscriber + code), paid_usd, refund_usd
  (succeeded only), net_usd, is_guest_order, customer_id (guests resolved
  by email via int_customer_identity), customer_resolution.
- Ben's calls: "gross" = pre-discount subtotal; net is NOT floored at zero
  (a test fails loudly instead).
- Hand-checked against the dbt-built views in MotherDuck: 3,650 orders =
  3,650 distinct order_ids; gross $194,283.64 - discount $4,874.85 = paid
  $189,408.79 (equals raw total_amount on every order); refund $6,546.82
  (equals int_orders_refunded); net $182,861.97; 1,257 guest orders = 28
  guest_email_match + 1,229 unresolved; 2,393 account orders; 0 negative
  net; 0 customer_ids missing from customers.
- Tests: not_null/unique/relationships/accepted_values in
  `_intermediate.yml`, plus 3 singular tests in `dbt/tests/`
  (no negative net; money reconciles to the cent; refund total matches
  int_orders_refunded).
- Note: `mart_storefront_revenue_monthly` still calls the paid amount
  "gross_revenue_usd". Point it at int_orders_net.paid_usd and rename the
  column at the marts review, so "gross" means one thing.
- File_Manifest.xlsx regenerated (271 rows). The manifest script now needs a
  fake HOME with Documents/ symlinks because folders mount by name.

## 2026-09-30 — int_orders_net built and tested in dbt

- `dbt build --select int_orders_net` on Ben's Mac: 1 view + 15 tests,
  PASS=16, ERROR=0, 10.2s. View in `dbt_dev_intermediate`.
- Checked the dbt-built view from MotherDuck: 3,650 rows = 3,650 distinct
  orders; gross $194,283.64, discount $4,874.85, paid $189,408.79, refund
  $6,546.82, net $182,861.97; 1,257 guest orders (28 guest_email_match,
  1,229 unresolved), 2,393 account orders; 0 negative net. All identical to
  the pre-build hand check.
- Playbook section 13 and double-black-solutions/LOG.md updated.

## 2026-09-30 — int_sessions_unified written and hand-verified (awaiting dbt build)

- New `int_sessions_unified` (one row per session, web + app): source_system,
  platform, started_at/ended_at/duration_seconds, customer_id,
  customer_resolution (known_at_time / backfilled / anonymous),
  anonymous_id, device_id, and the web-only UTM/landing/referrer/device columns.
- Ben's calls: keep the 4,994 app sessions with platform = 'web' as their
  own sessions (only 28 overlap in time with a web session); back-fill with
  no time limit (max gap today is 14 days).
- Hand-checked against the dbt-built views: 49,895 sessions = 30,285 web +
  19,610 app, all distinct; 26,086 known_at_time, 340 backfilled (263
  visitors), 23,469 anonymous; customer_id null exactly for the anonymous
  ones; 0 conflicts with a session's own customer; 0 negative durations; 0
  customer_ids missing from customers.
- Tests: not_null/unique/accepted_values/relationships in
  `_intermediate.yml` plus 3 singular tests in `dbt/tests/`.
- Ben pushed all earlier commits (0 unpushed at the start of this step).

## 2026-09-30 — int_sessions_unified built and tested in dbt

- `dbt build --select int_sessions_unified` on Ben's Mac: 1 view + 13 tests,
  PASS=14, ERROR=0, 10.2s. View in `dbt_dev_intermediate`.
- Checked from MotherDuck: 49,895 rows = 49,895 distinct sessions (30,285
  web, 19,610 app); 26,086 known_at_time, 340 backfilled (263 customers),
  23,469 anonymous (= null customer_id); 0 negative durations. Identical to
  the pre-build hand check.
- Playbook section 13 and double-black-solutions/LOG.md updated.

## 2026-09-29 — Overnight plan added

- `OVERNIGHT_PLAN.md`: runbook for a scheduled unattended run (Phase 3 models
  4-5, mart cleanup, up to 3 Phase 4 marts, Phase 5 descriptions). Commits go
  on a separate `overnight` branch, MotherDuck stays read-only, dbt cannot run
  overnight, results land in MORNING_LIST.md. Ben's calls: branch not master;
  assume-and-log decisions that are his.
- Plan revised (Ben): three scheduled runs (8:51 pm, 1:51 am, 6:51 am PT),
  one per usage-session reset; no unit cap; queue extended with Phase 6/7
  DRAFTS; each run resumes from MORNING_LIST.md "Progress".

## 2026-09-29 — Claude Code setup files added

- `CLAUDE.md` (standing rules for Claude Code sessions: same project, same
  rules, plus dbt builds and pushes of the `overnight` branch only),
  `.claude/settings.json` (allow dbt/git commit/push overnight; deny push to
  master, force push, reset --hard, clean, rm) and
  `OVERNIGHT_PLAN_CLAUDE_CODE.md` (overnight runbook variant where dbt builds
  and pushes are allowed). Cowork's OVERNIGHT_PLAN.md is unchanged.
- `.claude/settings.json` deny rules widened: they now also block bare
  `git push`, any push naming master/main (including `--dry-run` and
  `branch:master` forms), `--all`, `--mirror` and force flags. Only
  `git push origin overnight` is allowed.

## 2026-09-30 — int_messaging_events written and hand-verified (overnight run; needs dbt build)

- New `int_messaging_events` (one row per Braze email or push event, 36,232
  today = 26,335 email + 9,897 push): channel, send_id, campaign (+ name/type),
  event_name, occurred_at, customer_id, customer_resolution
  (braze_customer_id / email_match / unresolved), email_address (email only),
  device_id + platform (push only).
- Hand-checked against the dbt-built staging/intermediate views: event_ids
  distinct and no overlap between channels; 0 orphan campaigns; 0 customer_ids
  missing from customers; 0 events before their send; 0 conflicts between
  Braze's id and the email match; 2,187 email events had no customer_id, 44 of
  them resolve by email to an account, 2,143 stay unresolved (1,257 distinct
  guest addresses overall = the guest-order count); 7 email events are stamped
  after the data end (2026-07-30, latest 2026-08-01), kept and flagged.
- Tests: not_null/unique/accepted_values/relationships in `_intermediate.yml`
  plus 2 singular tests in `dbt/tests/`. NOT yet run in dbt.
- Assumed (needs Ben's call): no de-duplication; unique opens/clicks are the
  mart's job.

## 2026-09-30 — int_paid_media_daily written and hand-verified (overnight run; needs dbt build)

- New `int_paid_media_daily` (one row per platform per day; 6 platforms x
  1,095 days = 6,570 rows, 2023-08-01 to 2026-07-30): spend_usd, impressions,
  clicks, conversions, conversions_value_usd.
- Hand-checked against the dbt-built staging views: each platform has 1,095
  distinct dates with no gaps; no negative spend, clicks > impressions or
  conversions > clicks. Spend totals: meta $429,291.38, google_search
  $350,535.12 (ad-group table = keyword table), youtube $170,406.94, dv360
  $132,525.13, snap $115,034.09, tiktok $333,914.27.
- Assumed (needs Ben's call): conversion = Meta 'purchase' action only;
  other platforms use their single `conversions` column. Meta value is null.
  Snap swipes = clicks.
- Finding: raw Meta spend is plain dollars (project notes say cents); no
  conversion applied, verified raw sum = staged sum.
- Tests: yml (unique platform_day_id, accepted platforms, not_null) + 2
  singular tests. NOT yet run in dbt.

## 2026-09-30 — Phase 3 exit check: storefront mart reads int_orders_net (overnight run; needs dbt build)

- `mart_storefront_revenue_monthly` now reads `int_orders_net` instead of
  recomputing discounts/refunds from staging. Column `gross_revenue_usd`
  renamed `paid_revenue_usd` (it was the amount paid); new columns
  `gross_before_discount_usd`, `discount_usd` and `data_through`. yml
  descriptions and tests updated. Grep found no other readers of the old
  name (the Dive reads raw tables, not this mart).
- Hand-checked: re-running the new SQL against int_orders_net gave the same
  36 months as the dbt-built mart, every metric identical (order_count, paid,
  AOV, guest/discount/refund %, refunded amount, net). Totals: gross
  $194,283.64, discount $4,874.85, paid $189,408.79, net $182,861.97.
  has_discount = (discounts > 0) on all 3,650 orders (597).
- Needs `dbt build --select mart_storefront_revenue_monthly` on Ben's Mac.

## 2026-09-30 — mart_subscriber_movement_monthly written and hand-validated (overnight run; needs dbt build)

- New `mart_subscriber_movement_monthly` (CEO story "net-new vs churned paying
  subscribers"), one row per month, 2023-08 to 2026-07 (36 months):
  new_paying_subscribers (first_time / returning), churned_subscribers,
  net_new_subscribers, active_subscribers_end, data_through.
- New `int_subscription_data_through` (one date) so mart_mrr_monthly and this
  mart share the "where the data ends" rule; mart_mrr_monthly now reads it
  (logic identical: same greatest() of the same four columns; result
  2026-07-30 confirmed).
- Hand-validated against live views: 174 first-time + 25 returning = 199 new,
  101 churned, 98 active at 2026-07-31 (= 98 paid subscriptions never
  canceled = Phase 0's 98 active subscribers). Identity end = prev end + new -
  churned holds in all 36 months. Versus mart_mrr_monthly's 1st-of-month
  snapshot: 8 of 35 months differ, all with a start/cancel on the 1st itself.
  3 subscriptions paying from 2026-08-05 or later are past the data end, not
  counted.
- Tests: yml + 2 singular tests. NOT yet run in dbt. Needs
  `dbt build --select int_subscription_data_through mart_mrr_monthly mart_subscriber_movement_monthly`.

## 2026-09-30 — mart_paid_media_monthly and mart_acquisition_efficiency_monthly written and hand-validated (overnight run; need dbt build)

- Chosen from the persona stories (Performance Marketing: platform efficiency
  over time; CMO: spend per platform; CEO/CFO: CAC). Persona stories that
  need an ad-to-order key (channel-level CAC, campaign attribution) were NOT
  built: no such key exists.
- `mart_paid_media_monthly` (platform x month, 216 rows = 6 x 36): spend,
  impressions, clicks, platform-reported conversions/value, ctr_fraction,
  cpc_usd, cost_per_conversion_usd, reported_roas, data_through. Total spend
  $1,531,706.95; Google Search 2026-07 $8,224.52 spend, 2.35 reported ROAS.
- `mart_acquisition_efficiency_monthly` (month, 36 rows): paid spend, first-time
  paying subscribers (from mart_subscriber_movement_monthly), blended CAC,
  cumulative blended CAC. Overall $1,531,706.93 / 174 = $8,802.91; 2026-07
  $9,874.68 over 4; one month has no new subscribers (null CAC).
- Hand-validated by inlining int_paid_media_daily and the movement logic
  against live staging/intermediate views. Tests: yml + 2 singular tests.
  NOT yet run in dbt.

## 2026-09-30 — Phase 5 descriptions written (overnight run)

- Added a plain-language `description:` to every column of all 47 staging
  models (462 columns), all 8 intermediate models and all 5 marts, listing
  columns that previously had none (staging only described the tested keys).
  Existing model descriptions and all tests are unchanged (verified: same
  test set before and after for staging, intermediate and marts).
- Caveats written into the descriptions where a number could be misread:
  platform-reported conversions (not orders, overlap, fractional), raw micros
  vs _usd, payments include failed attempts, orders vs paid vs net (no
  margin), MRR/ARR are run-rates, guest/anonymous null customer_ids,
  utm_campaign is not an ad-platform key, Google keyword vs ad-group tables
  never added, blended CAC is not channel CAC, Meta value null.
- Descriptions for enumerated values (discount types, campaign types, etc.)
  were checked against the distinct values in the live staging views.
- The staging/intermediate/marts yml files were rewritten with PyYAML, so
  their formatting changed (block style, folded long text); content is
  otherwise the same. Not yet run through `dbt parse` / `dbt docs generate`
  (needs Ben's Mac).

## 2026-09-30 — Phase 6 DRAFT: semantic layer definitions (overnight run; not validated)

- `dbt/drafts/semantic_layer_DRAFT.yml`: 5 MetricFlow semantic models (mrr,
  subscriber_movement, storefront_revenue, paid_media, acquisition) and 25
  metrics, each defined once. Snapshot measures (MRR, active subscribers) use
  a non-additive time dimension so they are never summed across months.
  Ratios (AOV, CTR, CPC, cost per reported conversion, reported ROAS, blended
  CAC) are ratio metrics computed from sums.
- `docs/semantic_layer_validation_DRAFT.md`: 10 `mf query` checks with
  expected values from live hand SQL.
- Kept in `dbt/drafts/` (outside model-paths) so an unvalidated file cannot
  break `dbt build`. Assumed default: dbt Semantic Layer / MetricFlow.
- Honest limit: only paid-media metrics have two dimensions (platform, time).

## 2026-09-30 — Phase 7 DRAFT: Kinetic Skill document (overnight run)

- `docs/kinetic_skill_DRAFT.md`: which mart answers which question, every
  Phase 5 caveat restated as an instruction, and an explicit list of
  "say I don't have this data" cases (post-2026-07-30, margin/LTV, channel
  CAC/ROAS, churn rate/cohorts, email rates, individual customers).
- DRAFT: needs review by Ben (and, in a real engagement, the client's data
  owner), and the dbt build to pass, before use. Phase 8 not started.

## 2026-09-30 — Phase 5: metrics glossary and docs site branch

- `docs/metrics_glossary.md`: plain-language glossary of every metric in the
  five marts (Means / Not), with the same caveats as the descriptions.
- Built a `gh-pages` branch (local; three files from `dbt/target`:
  index.html, manifest.json, catalog.json, plus .nojekyll) so the generated
  dbt docs site can be served by GitHub Pages. The repo is public; the site
  has no local paths or secrets (checked). Needs `git push origin gh-pages`
  and Pages switched on (Settings > Pages > branch gh-pages, folder /root).
  The site is a snapshot of the 2026-09-30 build; regenerate and rebuild the
  branch after model changes.

## 2026-09-30 — Claude Code setup reviewed and updated (CLAUDE.md, settings, docs-site script)

- Reviewed CLAUDE.md and .claude/settings.json ahead of moving work to Claude Code.
  Fixed: rule 8 (playbook can now be updated from Claude Code: section-13-only
  edits, backup and per-section check, republish to the existing artifact link
  if the Artifact tool exists, else flag it); wrong unit note (Meta SPEND is
  dollars, only budgets are cents); playbook folder access (`--add-dir` and
  additionalDirectories, Edit allowed on playbook/ and LOG.md only); branch
  warning (work is on `overnight`, unmerged); static-dataset note;
  MORNING_LIST.md is record-only; Ben's teaching rules added.
- New `scripts/rebuild_docs_branch.sh`: rebuilds gh-pages from dbt/target as one
  commit on top of the existing branch (no force push). Tested here: adds one
  commit, second run says nothing to do; refuses local paths/token strings.
  `git push origin gh-pages` allowed in settings.
- Not verified from here: exact permission-pattern syntax for the ~ paths in
  settings.json and whether Claude Code has the Artifact tool. First Claude Code
  session should check both.

## 2026-09-30 — Model rule changed: choose per phase/task

- Ben's call: no fixed default model. At each phase or task Claude recommends the
  best and most cost-effective model and asks Ben to confirm before starting
  (first said "Opus by default", then revised the same day). Updated CLAUDE.md
  ("Model and cost") and HANDOFF.md. Ben also chose to keep Claude Code's auto
  permission mode on; the CLAUDE.md rules and settings.json deny rules still apply.
- The Cowork Project instructions (claude.ai) still contain the old MODEL & COST
  line; Ben edits those in the Project settings.

## 2026-09-30 — HANDOFF.md tidied for Claude Code (first Claude Code session)

- Setup check from Claude Code passed: playbook folder and LOG.md readable, the
  Artifact tool is available (published playbook read; republish to the same link
  is possible), `dbt debug` passes (it opens a MotherDuck browser login because no
  token is saved on the Mac).
- HANDOFF.md rewritten: status is now one line per phase; Cowork-only notes removed
  (Ben runs dbt, terminal cannot be typed into, device-bridge lock files, fake HOME
  for the manifest script, iCloud/sandbox pitfalls); git state corrected
  (`overnight` is pushed and in sync, 23 commits ahead of master, unmerged);
  resolved items moved to "Decisions already made"; new open items: merge of
  `overnight`, MotherDuck token, old lock files in `_to_delete/`.
- No models, data or playbook content changed.

## 2026-09-30 — Manifest script now runs from the dbt venv

- `python3 generator/build_manifest.py` failed on the Mac (system python3 has no
  openpyxl; the Cowork sandbox had it). Ben chose to install openpyxl into
  ~/.dbt-venv. The manifest is now run with
  `/Users/ben/.dbt-venv/bin/python generator/build_manifest.py`.
- Updated CLAUDE.md rule 2, HANDOFF.md and the allow rule in .claude/settings.json
  to that command. File_Manifest.xlsx rebuilt (299 file rows).

## 2026-09-30 — Merge of `overnight` into master decided (Ben runs it)

- Ben decided to merge `overnight` into master. Claude Code's auto mode blocked
  Claude from changing master, so nothing was merged by Claude. Ben runs:
  `git checkout master && git merge --ff-only overnight && git push origin master && git checkout overnight`.
  It is a fast-forward (master has no commits of its own), so no conflicts.
- HANDOFF.md updated with the command and how to check whether it has been done.

## 2026-09-30 — Phase 6 semantic layer validated (awaiting Ben's confirmation)

- Installed dbt-metricflow 0.11.0 (MetricFlow 0.209) into ~/.dbt-venv with dbt-core
  1.10.23 and dbt-duckdb 1.10.0 pinned; dbt-semantic-interfaces moved 0.9.0 -> 0.9.4.dev0.
- New model `metricflow_time_spine` (dbt_dev_marts): one row per day, 2023-01-01 to the
  data's last day (2026-07-30, read from int_subscription_data_through, not current_date).
- Draft moved from dbt/drafts/ to dbt/models/marts/_semantic_layer.yml. Fixes needed to
  pass validation: labels added to 7 metrics (required); the four `month` entities
  renamed per model (mrr_month, subscriber_movement_month, storefront_month,
  acquisition_month) because `month` is a reserved word and shared entity + dimension
  pairs are rejected. No metric definition changed.
- `mf validate-configs`: 0 errors, 0 warnings (definitions and warehouse checks).
- All 10 validation queries match the hand-computed expected values; results in
  docs/semantic_layer_validation.md (renamed from _DRAFT). Query 1 differs by one cent on
  four platforms: monthly rounding in the mart, not a definition error.
- Found: the platform dimension must be queried as `platform_month__platform`; the
  Phase 7 Skill draft must use that name.
- Full `dbt build`: 366/366 pass.
- Not done yet: playbook section 13, docs-site rebuild, phase marked done (all wait for
  Ben's confirmation).

## 2026-09-30 — Branch workflow: daytime on master, overnight only for unattended runs

- Ben merged `overnight` into master (fast-forward, both at b0fcdca) and pushed master himself.
- New pattern (Ben's call): interactive work happens on `master` (Claude commits locally, Ben
  pushes). Branch `overnight` is used only for unattended runs while he sleeps; he brings it up
  to date with master before a run and merges it back in the morning.
- Updated CLAUDE.md (start-of-session branch rule, rule 3), HANDOFF.md (Git status, open
  decision 1 resolved) and OVERNIGHT_PLAN_CLAUDE_CODE.md (branch check at run start).
- Also set up this day: MOTHERDUCK_TOKEN in ~/.zshrc so dbt/duckdb no longer prompt for a browser login.

## 2026-09-30 — Phase 6 closed; read-only SQL helper; fewer permission prompts

- Ben confirmed he understands the semantic layer (incl. why metrics cannot be sliced by each
  other: a dimension needs a label on the underlying rows). Phase 6 marked done in playbook
  section 13 (republished to the same artifact link, v26), double-black-solutions/LOG.md and HANDOFF.md.
- dbt docs regenerated and the gh-pages branch rebuilt locally (a339554); Ben publishes it with
  `git push origin gh-pages`.
- New scripts/md_select.py: runs ONE read-only statement on MotherDuck, refuses writes/DDL and
  multi-statement input, loads the token itself and never prints it. Tested: one good query,
  three refusals, a keyword inside a string literal. Allowed in .claude/settings.json (with
  mcp__terminal__read_terminal); CLAUDE.md rule 4 now points to it. Manifest line added.

## 2026-09-30 — Phase 7 started: Skill draft reviewed against live data (v2)

- Checked every mart, column and metric name in docs/kinetic_skill_DRAFT.md against MotherDuck: all
  exist. Quoted numbers hold: blended CAC $8,803 over 36 months, 4.8 first-time subscribers a
  month, 33.7% guest orders, Meta conversion value null in every month.
- Fixed: stale status note (models are built, semantic layer validated). Added "How to get the
  numbers": Ben chose SQL on the marts as the default route (works in claude.ai via the MotherDuck
  connector) and MetricFlow metrics where installed. Added the rules the SQL route needs
  (recompute ratios from sums, never sum snapshots, `ctr_fraction`) and the MetricFlow syntax
  (`platform_month__platform`, template filters). Manifest line updated.
- Not signed off yet: Ben is reading it.

## 2026-09-30 — Phase 7 signed off: Kinetic Skill v1

- Ben reviewed the Skill and answered the check questions (why no CAC by channel: no ad-to-subscriber
  key; why MRR is not summed: a snapshot would count the same subscribers every month). He accepted three scope decisions
  (Skill refuses churn rate/LTV/revenue by plan/email rates; dev schema pointer until Phase 8; SQL is
  the default route).
- Renamed docs/kinetic_skill_DRAFT.md to docs/kinetic_skill.md, removed the DRAFT wording, recorded the
  decisions in its header. Re-checked "about a third guest orders" against live data: 1,229 of 3,650
  orders (33.7%) have no customer_id. Manifest line updated.
- Playbook section 13, LOG.md and HANDOFF.md updated (Phase 8 is next).

## 2026-09-30 — Phase 8 pilot persona chosen: CMO

- Ben chose the CMO / performance marketing persona for the Phase 8 pilot (paid media is the richest
  data and has the most traps: platform-reported conversions, no CAC by channel). Next: scope one use case.
