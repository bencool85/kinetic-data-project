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
