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
  Since the 2026-09-30 addendum, messaging (channel, campaign type) and traffic (source,
  landing page) also have a second dimension; subscribers, MRR and storefront revenue
  can still be sliced by time only.
- Query 10 differs from the mart's monthly `blended_cac_usd` column on purpose: it is a
  ratio of sums over the whole period, not an average of monthly ratios.
- Add `--decimals 2` to see cents; by default the CLI shortens large numbers.

## Addendum 2026-09-30: owned channels (17 new metrics, 42 in total)

Added after Ben flagged that email, push and web/app traffic had no marts. New semantic
models `messaging` (mart_messaging_monthly) and `traffic` (mart_traffic_monthly).
`mf validate-configs`: 0 errors, 0 warnings. Full `dbt build`: 389/389 pass. The expected
values were worked out beforehand with direct SQL on `int_messaging_events` and
`int_sessions_unified`, not on the marts. New dimension names: `message_month__channel`,
`message_month__campaign_type`, `traffic_month__traffic_source`, `traffic_month__landing_page`.

| # | Command | Expected | Returned |
|---|---------|----------|----------|
| 11 | `mf query --metrics messages_sent,messages_opened,messages_clicked,message_open_rate,message_click_to_open_rate --group-by message_month__channel --decimals 4` | email 18,187 / 6,328 / 1,341 / 0.3549 / 0.2119; push 7,851 / 1,590 / 220 / 0.2080 / 0.1384 | identical |
| 12 | `mf query --metrics message_open_rate,message_click_to_open_rate --group-by message_month__campaign_type --where "{{ Dimension('message_month__channel') }} = 'email'" --decimals 4` | triggered 0.5505 / 0.3004; broadcast 0.2787 / 0.1438 | identical |
| 13 | `mf query --metrics messages_sent,messages_opened,message_open_rate,message_click_to_open_rate --group-by metric_time__year --decimals 4` | 2023 500 / 206 / 0.4187 / 0.2816; 2024 5,054 / 1,617 / 0.3263 / 0.1861; 2025 10,588 / 3,148 / 0.3040 / 0.1995; 2026 9,896 / 2,947 / 0.3047 / 0.1948 | identical |
| 14 | `mf query --metrics traffic_sessions,traffic_avg_session_seconds --decimals 1` | 49,895; 922.9 | identical |
| 15 | `mf query --metrics traffic_sessions,traffic_avg_session_seconds --group-by traffic_month__landing_page --where "{{ Dimension('traffic_month__traffic_source') }} = 'meta'" --decimals 1` | / 2,077 / 370.8; /blog 270 / 381.6; /courses 904 / 355.5; /pricing 1,154 / 371.2; /shop 839 / 361.4; /trial 607 / 341.8 | identical |
| 16 | `mf query --metrics traffic_sessions,traffic_known_share --group-by traffic_month__traffic_source --decimals 4` | app 19,610 / 1.0000; untagged_web 9,321 / 0.6186; meta 5,851 / 0.0518; google_search 4,823 / 0.0504 (others: tiktok 4,513, youtube 2,260, dv360 1,957, snap 1,547, email 13) | identical |

Notes:

- Rates are ratios of sums (e.g. 6,328 opens / 17,830 delivered), never averages of monthly rates.
- The marts and the intermediate models agree on every total (two singular tests per mart guard this).
