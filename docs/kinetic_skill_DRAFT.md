---
name: kinetic-data
description: How to answer business questions about Kinetic (a fictional D2C fitness company, synthetic data) from the MotherDuck `kinetic` database. Use for any question about subscribers, MRR, storefront revenue, paid media, CAC, or email/push. DRAFT: not reviewed by the client's data owner.
---

# Kinetic data Skill (DRAFT)

STATUS: DRAFT written overnight 2026-09-30. Not reviewed by Kinetic's data
owner (Phase 7 requires that), and it describes models that are written and
hand-verified but not yet built in dbt. Do not use with a pilot persona until
the dbt build passes and Ben has reviewed it.

## Ground rules

1. Query only the curated `dbt_dev_marts` tables below (and the semantic-layer
   metrics once validated). Do not build answers from raw tables or staging
   views when a mart exists.
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
