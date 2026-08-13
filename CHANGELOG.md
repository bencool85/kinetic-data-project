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
