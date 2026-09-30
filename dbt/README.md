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
  `products`, `product_variants` (Phase 1/2 core entities); `orders`, `order_line_items`,
  `payments`, `refunds`, `discount_codes` (Phase 3 storefront entities);
  `customer_addresses`, `devices`, `identity_map`, `segments`,
  `customer_segment_membership`, `subscription_events` (Customer 360);
  `web_sessions`, `web_events`, `app_sessions`, `app_events` (web/app
  engagement); `braze_email_campaigns`, `braze_email_events`,
  `braze_push_campaigns`, `braze_push_events` (email/push); the 4 `meta_*`
  tables (paid media: Meta); the 4 `google_search_*` tables (paid media:
  Google Search); the 3 `youtube_*` tables (paid media: YouTube); the 3
  `dv360_*` tables (paid media: DV360); the 4 `snap_*` tables (paid media:
  Snap); the 4 `tiktok_*` tables (paid media: TikTok) -- 47 of 47 raw
  tables staged
- Intermediate: `int_subscription_paid_periods` (trial-vs-paid start date
  logic), `int_orders_refunded`, `int_customer_identity`, `int_orders_net`,
  `int_sessions_unified`, `int_subscription_data_through`; written and
  hand-verified but awaiting `dbt build` (2026-09-30 overnight run):
  `int_messaging_events`, `int_paid_media_daily`
- Marts: `mart_mrr_monthly`, `mart_storefront_revenue_monthly` (now reads
  `int_orders_net`); awaiting `dbt build`: `mart_subscriber_movement_monthly`,
  `mart_paid_media_monthly`, `mart_acquisition_efficiency_monthly`
- Every model and column has a plain-language `description:` (Phase 5); run
  `dbt docs generate` to build the glossary site.

Still to come, table group by table group: segment membership (Phase 4),
web/app engagement (Phase 5), email/push funnels (Phase 6), paid media
CAC/ROAS (Phase 7).

## Running it yourself

Neither of Claude's environments (the cloud sandbox or the bridge to this
Mac) can reach `motherduck.com` directly -- outbound network from both is
restricted to an allowlist that doesn't include it. So every model here was
validated by running its equivalent SQL directly against the live database
via the MotherDuck MCP connection (the same live-validation discipline used
for the original 47 tables), but **actually executing `dbt run`/`dbt test`
has to happen from your own Mac**, which has normal, unrestricted internet
access.

One-time setup (Terminal on your Mac). dbt goes in its own virtual
environment so it can't clash with other Python tools:

```
python3 -m venv ~/.dbt-venv
source ~/.dbt-venv/bin/activate
pip install dbt-core dbt-duckdb
```

The connection profile lives in this folder (`dbt/profiles.yml`), so there
is nothing to add under `~/.dbt`. It uses `schema: dbt_dev`, so dbt's output
lands in `dbt_dev_staging`, `dbt_dev_intermediate` and `dbt_dev_marts`,
separate from the raw tables in `main`.

`dbt-duckdb` reads your MotherDuck auth the same way the `duckdb` CLI does
(a saved login, or the `motherduck_token` environment variable).

Each time, from this `dbt/` folder:

```
source ~/.dbt-venv/bin/activate
dbt debug  # checks the connection
dbt run    # builds all staging/intermediate/mart views & tables
dbt test   # runs the not_null/unique/relationship tests
```
