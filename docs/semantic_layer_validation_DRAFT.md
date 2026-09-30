# Semantic layer validation set (DRAFT)

Written overnight 2026-09-30. Nothing here has been run: MetricFlow is not
installed and the marts are not built in dbt yet. Expected values below come
from hand SQL against the live dbt_dev_* staging/intermediate views (and, for
subscribers, the verified mart logic), so they are what the marts SHOULD
return. Run each `mf query` after `dbt build` and compare.

Metric definitions: `dbt/drafts/semantic_layer_DRAFT.yml`.

| # | Command | Expected |
|---|---------|----------|
| 1 | `mf query --metrics paid_spend_usd --group-by platform --where "metric_time__year = '2025-01-01'"` | dv360 49,348.97; google_search 127,428.75; meta 154,124.07; snap 41,171.10; tiktok 131,666.08; youtube 64,295.10 |
| 2 | `mf query --metrics paid_ctr --group-by platform --where "metric_time__year = '2025-01-01'"` | dv360 0.0039; google_search 0.0451; meta 0.0153; snap 0.0111; tiktok 0.0137; youtube 0.0029 (Snap uses swipes as clicks) |
| 3 | `mf query --metrics paid_spend_usd --group-by metric_time__month --where "platform = 'google_search'" --start-time 2026-07-01 --end-time 2026-07-31` | 8,224.52 |
| 4 | `mf query --metrics paid_reported_roas --group-by platform --where "metric_time__month = '2026-07-01' and platform = 'google_search'"` | 2.35 |
| 5 | `mf query --metrics storefront_paid_revenue_usd,storefront_net_revenue_usd,storefront_aov_usd --group-by metric_time__year` | 2023: 5,711.36 / 5,452.27 / 46.06; 2024: 39,843.85 / 38,630.60 / 50.50; 2025: 71,543.09 / 68,835.72 / 52.88; 2026: 72,310.49 / 69,943.38 / 52.25 |
| 6 | `mf query --metrics storefront_paid_revenue_usd` (no grouping) | 189,408.79 (gross 194,283.64 minus discount 4,874.85) |
| 7 | `mf query --metrics new_paying_subscribers,first_time_subscribers,returning_subscribers,churned_subscribers,net_new_subscribers` | 199, 174, 25, 101, 98 |
| 8 | `mf query --metrics active_subscribers_month_end --group-by metric_time__month --start-time 2026-07-01 --end-time 2026-07-31` | 98 |
| 9 | `mf query --metrics mrr_usd --group-by metric_time__month --start-time 2026-07-01 --end-time 2026-07-31` | 2,133.07 |
| 10 | `mf query --metrics blended_cac_usd` | 8,802.91 (1,531,706.93 / 174) |

Notes for the checker:

- Query 9 should equal mart_mrr_monthly for 2026-07. `mrr_usd` over a longer
  period returns the last month's snapshot, not a sum; verify this once with
  `--group-by metric_time__year`.
- Queries 1-4 are the "at least two approved dimensions" evidence (platform
  and time). Nothing else can be sliced by anything except time yet.
- Query 10 will differ from the mart's monthly `blended_cac_usd` column
  because it is a ratio of sums over the whole period, not an average of
  monthly ratios.
- Expected values in 5-6 came from int_orders_net, which the storefront mart
  now reads, so they should match to the cent.
