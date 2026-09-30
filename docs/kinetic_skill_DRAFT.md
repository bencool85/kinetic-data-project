---
name: kinetic-data
description: How to answer business questions about Kinetic (a fictional D2C fitness company, synthetic data) from the MotherDuck `kinetic` database. Use for any question about subscribers, MRR, storefront revenue, paid media, CAC, or email/push. DRAFT: not reviewed by the client's data owner.
---

# Kinetic data Skill (DRAFT)

STATUS: DRAFT v2 (2026-09-30), in review with Ben (Phase 7). The five marts
are built (full build 366/366 pass) and the semantic layer is validated (10/10
queries match hand-computed values). Table, column and metric names below were
checked against the live database on 2026-09-30. Do not use with a pilot
persona until Ben has signed it off.

## Ground rules

1. Query only the curated `kinetic.dbt_dev_marts` tables below, or the
   semantic-layer metrics that sit on top of them (see "How to get the
   numbers"). Do not build answers from raw tables or staging views when a
   mart exists.
2. Every answer states the metric name, the period, and the `data_through`
   date. The data ends 2026-07-30. Never answer for later months, and never
   treat "no row" as zero.
3. Lead with the number, then the caveat that applies. If a caveat below
   applies and you leave it out, the answer is wrong.
4. Money is US dollars. Ad platforms report in micros or cents upstream; the
   marts are already dollars. Do not convert again.

## Which mart answers which question

| Question | Use | Grain |
|----------|-----|-------|
| MRR, ARR, how many paying subscribers on the 1st | `mart_mrr_monthly` | month |
| Are we adding more paying subscribers than we lose? New, returning, churned, net new, paying at month end | `mart_subscriber_movement_monthly` | month |
| Course and merch revenue, AOV, discounts, refunds, guest checkout share | `mart_storefront_revenue_monthly` | month |
| Spend, clicks, CTR, CPC, cost per conversion by ad platform | `mart_paid_media_monthly` | platform x month |
| What does it cost us to get a subscriber? | `mart_acquisition_efficiency_monthly` | month |

Persona guide: CEO -> subscriber movement, MRR, blended CAC. CFO -> storefront
revenue (paid vs net), MRR, blended CAC. CMO / performance marketing -> paid
media, blended CAC.

## How to get the numbers

Two routes return the same numbers (checked on 10 test queries, 2026-09-30).

**Route 1 (default, works anywhere): SQL on the marts.** Read-only SELECTs
against `kinetic.dbt_dev_marts.<mart>`. Rules for this route:

- Money columns end in `_usd`; rates in `mart_paid_media_monthly` are
  `ctr_fraction` (0.0153 means 1.53%).
- Ratios over more than one month or platform (AOV, CTR, CPC, cost per
  conversion, reported ROAS, blended CAC) must be recomputed from the sums,
  e.g. AOV = sum(paid_revenue_usd) / sum(order_count). Never average the
  monthly ratio columns.
- Snapshots (`mrr_usd`, `arr_usd`, `active_subscribers`,
  `active_subscribers_end`) are never summed across months: take the last
  month of the period.
- Filter with `month_start` (a DATE, first of the month). Every mart has a
  `data_through` column; quote it.

**Route 2 (only where MetricFlow is installed, e.g. Claude Code on Ben's
Mac): semantic-layer metrics.** Run `mf query` from the `dbt/` folder. The
metric already applies the rules above (ratios from sums, snapshots take the
last value), so prefer it when available.

| Metric | Same as mart column |
|--------|---------------------|
| `mrr_usd`, `active_subscribers` | `mart_mrr_monthly` |
| `new_paying_subscribers`, `first_time_subscribers`, `returning_subscribers`, `churned_subscribers`, `net_new_subscribers`, `active_subscribers_month_end` | `mart_subscriber_movement_monthly` (last one = `active_subscribers_end`) |
| `storefront_orders`, `storefront_gross_before_discount_usd`, `storefront_paid_revenue_usd`, `storefront_net_revenue_usd`, `storefront_aov_usd` | `mart_storefront_revenue_monthly` (`order_count`, ...) |
| `paid_spend_usd`, `paid_impressions`, `paid_clicks`, `paid_reported_conversions`, `paid_reported_conversion_value_usd`, `paid_ctr`, `paid_cpc_usd`, `paid_cost_per_reported_conversion_usd`, `paid_reported_roas` | `mart_paid_media_monthly` |
| `acq_paid_spend_usd`, `acq_first_time_subscribers`, `blended_cac_usd` | `mart_acquisition_efficiency_monthly` |

MetricFlow syntax that trips people up:

- Time: `--group-by metric_time__month` (or `__quarter`, `__year`).
- Platform: `--group-by platform_month__platform`. Plain `platform` is
  rejected. Only paid-media metrics have a platform; nothing else can be
  split by any dimension other than time.
- Filters use templates:
  `--where "{{ TimeDimension('metric_time','year') }} = '2025-01-01'"` or
  `--where "{{ Dimension('platform_month__platform') }} = 'google_search'"`.
  Date ranges: `--start-time 2026-07-01 --end-time 2026-07-31`.
- Add `--decimals 2` to see cents.
- Example: `mf query --metrics paid_spend_usd --group-by platform_month__platform --where "{{ TimeDimension('metric_time','year') }} = '2025-01-01'"`

## Caveats, restated as instructions

- MRR and ARR are run-rates from plan prices (annual plans divided by 12),
  not cash collected. Say "run-rate". ARR is MRR times 12, not a forecast.
- Never sum MRR or active-subscriber snapshots across months. For a quarter or
  year use the last month's value.
- "Paying subscriber" starts when the trial converts. A trial canceled before
  converting was never a paying subscriber and is not "churn".
- `returning_subscribers` are win-backs (they had an earlier paying
  subscription). When asked for "new customers", say whether returning ones
  are included.
- Storefront revenue: `paid_revenue_usd` is what customers were charged after
  discounts and before refunds (it was called gross_revenue_usd before
  2026-09-30). `gross_before_discount_usd` is before discounts. `net_revenue_usd`
  is paid minus refunds. Always state which one you are quoting. Never call
  net revenue "margin" or "profit": there is no cost data.
- `refunded_amount_usd` is attributed to the month of the ORDER, not the month
  the refund was paid.
- Paid media conversions and conversion value are each platform's own claims.
  They overlap across platforms, can be fractional, and are not Kinetic
  orders. Never add them across platforms and call the total "sales", never
  compare them one-to-one with orders, and never call `reported_roas` "true
  ROAS".
- Meta's conversion is its 'purchase' action only and Meta reports no
  conversion value, so `reported_roas` is null for Meta. Exclude Meta or say
  it is missing; never treat null as zero return.
- Snap "clicks" are swipe-ups. DV360's budget is monthly, others daily. Budgets
  anywhere are today's setting, not history.
- Google Search: spend exists at ad-group and keyword level; they are the same
  money. Never add both.
- Blended CAC = all paid spend / first-time paying subscribers. It includes
  organic sign-ups, so it overstates the cost of an ad-driven subscriber. It
  cannot be split by channel or campaign: no key links an ad to a session,
  order or subscriber. Monthly CAC is noisy (about 5 sign-ups a month); prefer
  quarter/year or `cumulative_blended_cac_usd`. Null means no new subscribers
  that month. The absolute level ($8.8k per subscriber overall) is a
  synthetic-data artifact, not a benchmark.
- `utm_campaign` and `utm_source` on web sessions are URL tags, not ad platform
  campaign IDs. Do not use them to attribute revenue to an ad campaign.
- Guest orders (about a third) have no customer_id unless matched by email;
  anonymous web visitors are most of web traffic. Do not report "customers"
  counts from tables where identity is partial without saying so.

## When to say "I don't have this data"

Say it plainly, and stop, instead of guessing, when the question needs:

- anything after 2026-07-30, forecasts, or targets/budgets history;
- profit, margin, cost of goods, or LTV (there is no product cost data, and
  no LTV mart exists yet);
- CAC or ROAS by channel, campaign, ad or creative that claims real causation
  (only platform-reported figures and one blended CAC exist);
- churn RATE, retention cohorts, or revenue by subscriber plan/tier (no mart
  yet; movement counts exist, rates do not);
- email/push performance (open rate, click rate): `int_messaging_events`
  exists but no mart defines the rate, so do not compute ad hoc unique-open
  numbers as if they were the official metric;
- individual customers' data. This Skill answers business-level questions only.

When a question is close to something a mart answers, say what the nearest
available number is and which caveat separates it from what was asked.

## Escalation

If a number looks wrong (negative net new when trends say otherwise, a
platform with zero spend, a month missing), do not smooth it over. Report the
figure as returned, note the anomaly, and tell the user to raise it with
Kinetic's data owner.
