---
name: kinetic-data
description: How to answer business questions about Kinetic (a fictional D2C fitness company, synthetic data) from the MotherDuck `kinetic` database. Use for any question about subscribers, MRR, storefront revenue, paid media, CAC, email and push messaging, or web and app traffic. v1 signed off by the data owner (Ben) on 2026-09-30; v1.2 additions (owned channels) built and validated, awaiting his review.
---

# Kinetic data Skill

STATUS: v1.2 (v1 signed off by Ben, Phase 7, 2026-09-30; v1.1 added the read-only
rule; v1.2, 2026-09-30, adds the owned-channel marts for email/push and web/app
traffic and the no-causal-wording rule). The seven marts are built (full build
389/389 pass) and the semantic layer (42 metrics) is validated (16/16 queries
match hand-computed values). Table, column and metric names below were checked
against the live database on 2026-09-30. The v1.2 additions have NOT yet been
reviewed by Ben; the definitions behind them (open rate = opens / delivered,
delivered = sends - bounces, traffic_source grouping) are assumed defaults
waiting for his OK.

Scope decisions Ben made at sign-off:
- Churn rate, LTV and revenue by plan have no mart yet; the Skill refuses them
  rather than computing ad hoc. Email/push and web/app traffic now have marts
  (v1.2) but only at channel / campaign-type / source / landing-page level.
- The SQL route points at the dev schema `dbt_dev_marts`. Phase 8 pilot (Ben,
  2026-09-30): stays on dev because the data is static; a stable production
  schema is required before any real client.
- SQL on the marts is the default route; MetricFlow only runs where it is installed.

## Ground rules

1. Query only the curated `kinetic.dbt_dev_marts` tables below, or the
   semantic-layer metrics that sit on top of them (see "How to get the
   numbers"). Do not build answers from raw tables or staging views when a
   mart exists.
2. Every answer states the metric name, the period, and the `data_through`
   date. The data ends 2026-07-30. Never answer for later months, and never
   treat "no row" as zero.
3. Read only. Run SELECT statements only; never CREATE, INSERT, UPDATE,
   DELETE, DROP or ALTER anything, and never use a write/read-write query tool.
   If a question seems to need a write, stop and say so.
4. Lead with the number, then the caveat that applies. If a caveat below
   applies and you leave it out, the answer is wrong.
5. No causal wording. Never say spend "brought in", "drove", "generated" or
   "delivered" subscribers, revenue or sessions, and never say a message or
   traffic source "caused" an outcome. Say "spend of $X alongside N
   first-time subscribers". No key links an ad, message or session to an
   order or subscriber; these are side-by-side numbers, not attribution.
6. Money is US dollars. Ad platforms report in micros or cents upstream; the
   marts are already dollars. Do not convert again.

## Which mart answers which question

| Question | Use | Grain |
|----------|-----|-------|
| MRR, ARR, how many paying subscribers on the 1st | `mart_mrr_monthly` | month |
| Are we adding more paying subscribers than we lose? New, returning, churned, net new, paying at month end | `mart_subscriber_movement_monthly` | month |
| Course and merch revenue, AOV, discounts, refunds, guest checkout share | `mart_storefront_revenue_monthly` | month |
| Spend, clicks, CTR, CPC, cost per conversion by ad platform | `mart_paid_media_monthly` | platform x month |
| What does it cost us to get a subscriber? | `mart_acquisition_efficiency_monthly` | month |
| Email and push: sends, bounces, opens, clicks, unsubscribes and their rates | `mart_messaging_monthly` | channel x campaign type x month |
| Web and app traffic: sessions by source and landing page, known vs anonymous, session length | `mart_traffic_monthly` | traffic source x landing page x month |

Persona guide: CEO -> subscriber movement, MRR, blended CAC. CFO -> storefront
revenue (paid vs net), MRR, blended CAC. CMO / performance marketing -> paid
media, messaging, traffic, blended CAC.

## How to get the numbers

Two routes return the same numbers (checked on 16 test queries, 2026-09-30).

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
- Messaging and traffic marts: counts (`sends`, `opens`, `sessions`, ...) add up
  across months, channels and sources; the `*_rate_fraction`, `known_share_fraction`
  and `avg_session_seconds` columns do not. Recompute them from sums, e.g. open
  rate = sum(opens) / sum(delivered); average session = sum(total_duration_seconds)
  / sum(sessions).
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
| `messages_sent`, `messages_bounced`, `messages_delivered`, `messages_opened`, `messages_clicked`, `messages_unsubscribed`, `message_bounce_rate`, `message_open_rate`, `message_click_rate`, `message_click_to_open_rate`, `message_unsubscribe_rate` | `mart_messaging_monthly` |
| `traffic_sessions`, `traffic_known_sessions`, `traffic_anonymous_sessions`, `traffic_duration_seconds`, `traffic_known_share`, `traffic_avg_session_seconds` | `mart_traffic_monthly` |

MetricFlow syntax that trips people up:

- Time: `--group-by metric_time__month` (or `__quarter`, `__year`).
- Platform: `--group-by platform_month__platform`. Plain `platform` is
  rejected. Only paid-media metrics have a platform.
- Messaging: `--group-by message_month__channel` (email, push) or
  `message_month__campaign_type` (broadcast, triggered).
- Traffic: `--group-by traffic_month__traffic_source` or
  `traffic_month__landing_page`. Plain names are rejected.
- Subscribers, MRR, storefront and blended CAC can be split by time only.
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
- Email and push are counted in MESSAGES, not people. `delivered` is sends minus
  bounces (there is no delivered event); open, click and unsubscribe rates divide
  by delivered, click-to-open divides by opens. An open is a tracked event defined
  by this dataset: compare channels and months, never to outside benchmarks. A
  month means messages SENT that month. Triggered messages (sent after a customer
  action) open about twice as often as broadcasts, so never blend the two without
  saying so. Seven opens stamped 31 Jul-1 Aug 2026 belong to 29-30 Jul sends and
  are in July; the latest month is cut off at the data's end.
- Traffic: a session is a visit, not a person or a sale. `traffic_source` is the
  UTM source for tagged web sessions (meta, google_search, tiktok, youtube, dv360,
  snap, email), `untagged_web` for web sessions with no tag (direct, organic and
  untracked cannot be told apart) and `app` for all app sessions (no tags, no
  landing page, all known customers). About 95% of paid-tagged sessions are
  anonymous, so `known_share` for paid sources is low by nature. Never credit
  revenue or subscribers to a source, and do not divide ad-platform clicks by
  sessions as if they should match.
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
- email or push performance at CAMPAIGN or individual-message level (only
  channel and campaign type exist), revenue, orders or subscribers that came from
  an email, push message or traffic source (no key links them), or opens by
  person (the unit is messages);
- page-level behavior beyond the landing page (funnels, clicks on a page,
  bounce rate);
- individual customers' data. This Skill answers business-level questions only.

When a question is close to something a mart answers, say what the nearest
available number is and which caveat separates it from what was asked.

## Escalation

If a number looks wrong (negative net new when trends say otherwise, a
platform with zero spend, a month missing), do not smooth it over. Report the
figure as returned, note the anomaly, and tell the user to raise it with
Kinetic's data owner.
