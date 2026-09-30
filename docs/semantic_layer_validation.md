# Semantic layer validation set

Run on 2026-09-30 with MetricFlow 0.209 (dbt-metricflow 0.11.0) against the built
marts in MotherDuck. Result: `mf validate-configs` reports 0 errors and 0 warnings,
and all 10 queries below return the expected values. The expected values were
worked out beforehand by hand SQL against the staging/intermediate views, so this
is an independent check, not the marts agreeing with themselves.

Metric definitions: `dbt/models/marts/_semantic_layer.yml`. Run the commands from `dbt/`.

Naming that matters: the platform dimension must be written `platform_month__platform`
(entity name, two underscores, dimension name). Plain `platform` is rejected. Time
filters use the template form shown below.

| # | Command | Expected | Returned |
|---|---------|----------|----------|
| 1 | `mf query --metrics paid_spend_usd --group-by platform_month__platform --where "{{ TimeDimension('metric_time','year') }} = '2025-01-01'"` | dv360 49,348.97; google_search 127,428.75; meta 154,124.07; snap 41,171.10; tiktok 131,666.08; youtube 64,295.10 | dv360 49,348.96; google_search 127,428.76; meta 154,124.07; snap 41,171.09; tiktok 131,666.09; youtube 64,295.10 (match, see rounding note) |
| 2 | `mf query --metrics paid_ctr --group-by platform_month__platform --where "{{ TimeDimension('metric_time','year') }} = '2025-01-01'"` | dv360 0.0039; google_search 0.0451; meta 0.0153; snap 0.0111; tiktok 0.0137; youtube 0.0029 (Snap uses swipes as clicks) | identical |
| 3 | `mf query --metrics paid_spend_usd --group-by metric_time__month --where "{{ Dimension('platform_month__platform') }} = 'google_search'" --start-time 2026-07-01 --end-time 2026-07-31` | 8,224.52 | 8,224.52 |
| 4 | `mf query --metrics paid_reported_roas --group-by platform_month__platform --where "{{ TimeDimension('metric_time','month') }} = '2026-07-01' and {{ Dimension('platform_month__platform') }} = 'google_search'"` | 2.35 | 2.35 |
| 5 | `mf query --metrics storefront_paid_revenue_usd,storefront_net_revenue_usd,storefront_aov_usd --group-by metric_time__year` | 2023: 5,711.36 / 5,452.27 / 46.06; 2024: 39,843.85 / 38,630.60 / 50.50; 2025: 71,543.09 / 68,835.72 / 52.88; 2026: 72,310.49 / 69,943.38 / 52.25 | identical |
| 6 | `mf query --metrics storefront_paid_revenue_usd,storefront_gross_before_discount_usd` (no grouping) | 189,408.79 (gross 194,283.64 minus discount 4,874.85) | 189,408.79; gross 194,283.64 |
| 7 | `mf query --metrics new_paying_subscribers,first_time_subscribers,returning_subscribers,churned_subscribers,net_new_subscribers` | 199, 174, 25, 101, 98 | identical |
| 8 | `mf query --metrics active_subscribers_month_end --group-by metric_time__month --start-time 2026-07-01 --end-time 2026-07-31` | 98 | 98 |
| 9 | `mf query --metrics mrr_usd --group-by metric_time__month --start-time 2026-07-01 --end-time 2026-07-31` | 2,133.07 | 2,133.07 |
| 10 | `mf query --metrics blended_cac_usd` | 8,802.91 (1,531,706.93 / 174) | 8,802.91 |

Notes:

- Rounding (query 1): four platforms differ from the hand figure by one cent. The mart
  rounds each month's spend to cents and the semantic layer adds up those 12 rounded
  months; the hand figure added the unrounded days. The differences cancel out across
  platforms. Not an error in the definitions.
- Snapshot check (extra query 9b, `mf query --metrics mrr_usd,active_subscribers
  --group-by metric_time__year`): returns the LAST month's snapshot per year, not a
  sum: 2023 156.03 / 7; 2024 643.19 / 27; 2025 1,312.54 / 55; 2026 2,133.07 / 90.
- Queries 1-4 are the "at least two approved dimensions" evidence (platform and time).
  Nothing else can be sliced by anything except time yet.
- Query 10 differs from the mart's monthly `blended_cac_usd` column on purpose: it is a
  ratio of sums over the whole period, not an average of monthly ratios.
- Add `--decimals 2` to see cents; by default the CLI shortens large numbers.
