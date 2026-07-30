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

Planning complete. Next step: build Phase 0 (the master timeline simulation).
See `docs/generation_plan.md` for the full build sequence.
