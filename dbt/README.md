# Kinetic semantic layer (dbt)

This is the "semantic layer" step from the project's original roadmap
(raw data -> data platform -> **semantic layer** -> AI agents). It sits on
top of the 47 raw tables already live in the MotherDuck `kinetic` database
and defines canonical, tested metric logic on top of them -- so "MRR" or
"active subscribers" means exactly one thing, defined once, instead of
being recomputed slightly differently in every dashboard query.

## Structure (standard dbt layering)

- `models/staging/` -- one model per raw table, 1:1, light renaming/casting
  only. No business logic here.
- `models/intermediate/` -- reusable business logic that more than one mart
  needs (e.g. "when did this subscription actually start being a paying
  subscription" -- trials complicate this, so it's computed once here).
- `models/marts/` -- the actual canonical metrics analysts/dashboards query.

This mirrors the same incremental discipline as the original 47-table build:
one small group of models at a time, each validated against the live
database before moving on -- not the whole semantic layer in one shot.

## What's built so far

- Staging: `customers`, `subscriptions`, `subscription_plans`, `invoices`,
  `products` (the Phase 1/2 core entities)
- Intermediate: `int_subscription_paid_periods` (resolves the trial-vs-paid
  start date logic used everywhere else in this project)
- Marts: `mart_mrr_monthly` (active subscriber count + MRR by month)

Everything else in `docs/generation_plan.md`'s "Canonical metrics" list
(ARR, churn, CAC/LTV, course/merch revenue, etc.) is still to come, table
group by table group.

## Running it yourself

Neither of Claude's environments (the cloud sandbox or the bridge to this
Mac) can reach `motherduck.com` directly -- outbound network from both is
restricted to an allowlist that doesn't include it. So every model here was
validated by running its equivalent SQL directly against the live database
via the MotherDuck MCP connection (the same live-validation discipline used
for the original 47 tables), but **actually executing `dbt run`/`dbt test`
has to happen from your own Mac**, which has normal, unrestricted internet
access.

One-time setup:

```
pip3 install dbt-core dbt-duckdb
```

Add a profile at `~/.dbt/profiles.yml`:

```yaml
kinetic:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: 'md:kinetic'
      threads: 4
```

`dbt-duckdb` reads your MotherDuck auth the same way the `duckdb` CLI does
(a saved token via `duckdb -ui` login, or the `motherduck_token` environment
variable) -- no separate credential needed if you're already logged in to
MotherDuck on this machine.

Then, from this `dbt/` folder:

```
dbt run    # builds all staging/intermediate/mart views & tables
dbt test   # runs the not_null/unique/relationship tests
```
