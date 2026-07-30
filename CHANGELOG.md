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
