# Kinetic Synthetic Data Project

Synthetic dataset for **Kinetic**, a fictional online fitness platform (subscriptions +
a la carte training courses + branded merch/gear), built to feed a full BI modernization
stack: raw data → data platform (Snowflake/dbt-style) → semantic layer/canonical metrics
→ AI agents.

## Folder structure

```
kinetic-project/
├── README.md              This file
├── CHANGELOG.md           Plain-English log of what changed at each step
├── docs/                  Business context, schema reference, generation plan
├── internal/              Debug/ground-truth artifacts (not part of the shipped schema)
│   ├── _sim_customer_timeline.json
│   ├── _sim_customer_timeline_summary.csv
│   ├── _sim_seasonality_calendar.csv
│   ├── _sim_attribution_ground_truth.json
│   └── _sim_anonymous_population.csv
└── data/                  The 47 final CSV tables, added phase by phase
```

## Status

All 47 tables built, individually validated, and cross-dataset audited (see
`docs/cross_dataset_alignment_audit.md`). Loaded into MotherDuck as the live
`kinetic` database. A `dbt` semantic layer (staging -> intermediate -> marts,
canonical metric definitions) is being built on top -- see `dbt/README.md`
once that folder exists.

## Live dashboard

The MotherDuck Dive (5 tabs: Overview / CEO / CMO / CFO / Performance
Marketing, 8 persona-specific stories, all live-queried against the real
data) is here:

https://app.motherduck.com/dives/kinetic-marketing-revenue-overview-58909b4e-d301-4794-bb59-ce46f9dc73a6

## Source of truth

- **This repo** (`github.com/bencool85/kinetic-data-project`) -- code,
  generators, docs, full history.
- **MotherDuck `kinetic` database** -- the live warehouse the Dive queries.
- Working git clone lives at `~/Documents/kinetic-project` on Ben's Mac
  (kept outside iCloud sync on purpose -- see `CHANGELOG.md`, 2026-09-28
  entry, for why).
