# Kinetic metrics glossary

Plain-language definitions of every metric in the marts, and what each one does NOT mean. Kinetic is a fictional company with a synthetic, static dataset; **all data ends 2026-07-30**, and every table stops at that date. Money is in US dollars. Column-level detail is in the dbt docs site; this page is the quick reference.

How to read an entry: **Means** (what it is), **Grain** (what one row is), **Source** (which mart), **Not** (the misreading to avoid).

---

## Recurring revenue (`mart_mrr_monthly`, one row per month, snapshot on the 1st)

**MRR (`mrr_usd`)**
- Means: the monthly value of every subscription that is paying on the 1st of the month. Annual plans count as price ÷ 12.
- Not: cash collected, or a forecast. It is a run-rate. Never add MRR across months.

**ARR (`arr_usd`)**
- Means: MRR × 12.
- Not: a forecast or a contract value.

**Active subscribers (`active_subscribers`)**
- Means: paying subscriptions on the 1st of the month. A subscription starts paying when its trial converts.
- Not: trial users, or people who ever subscribed.

## Subscriber movement (`mart_subscriber_movement_monthly`, one row per month)

**New paying subscribers (`new_paying_subscribers`)**
- Means: subscriptions whose paying started that month (first-time + returning).
- Not: trial starts. A trial canceled before converting never paid and never appears here.

**First-time / returning (`first_time_subscribers`, `returning_subscribers`)**
- Means: first-time = the customer had never paid before; returning = a win-back with an earlier paying subscription.
- Not: acquisition by ads. Returning subscribers are excluded from CAC.

**Churned subscribers (`churned_subscribers`)**
- Means: paying subscriptions canceled that month.
- Not: a churn RATE (none is defined yet), and not canceled trials.

**Net new (`net_new_subscribers`)** = new paying − churned. Negative means the paying base shrank.

**Active at month end (`active_subscribers_end`)**
- Means: paying and not canceled on the last day of the month.
- Not: identical to MRR's `active_subscribers`, which is counted on the 1st (they differ only when someone starts or cancels on the 1st).

## Storefront revenue (`mart_storefront_revenue_monthly`, one row per month; courses and merch only)

**Gross before discount (`gross_before_discount_usd`)**: order subtotals before any discount.
**Discount (`discount_usd`)**: subscriber discounts plus discount codes.
**Paid revenue (`paid_revenue_usd`)**
- Means: what customers were charged (gross − discount), before refunds. Was called `gross_revenue_usd` before 2026-09-30.
- Not: gross sales, and not net of refunds.

**Net revenue (`net_revenue_usd`)**
- Means: paid revenue − successful refunds.
- Not: margin or profit. There is no cost data in this dataset.

**AOV (`aov_usd`)**: paid revenue ÷ orders.
**Refunded amount / refunded order % (`refunded_amount_usd`, `refunded_order_pct`)**
- Means: refunds counted against the month of the ORDER, not the month the refund was paid.

**Guest order % / discount used %**: share of orders (0-100) that were guest checkouts / used any discount. Guest orders have no account unless matched by email.

Subscriptions are not in this mart; they are billed through invoices (see MRR).

## Paid media (`mart_paid_media_monthly`, one row per platform per month)

Platforms: meta, google_search, youtube, dv360, snap, tiktok.

**Spend (`spend_usd`)**: advertising cost. Already in dollars (platform micros converted upstream).
**Impressions / clicks**: times shown / clicked. Snap "clicks" are swipe-ups.
**CTR (`ctr_fraction`)**: clicks ÷ impressions as a fraction (0.045 = 4.5%).
**CPC (`cpc_usd`)**: spend ÷ clicks.

**Conversions (`conversions`, `conversions_value_usd`)**
- Means: what each platform CLAIMS it drove. Meta counts only its `purchase` action; the other platforms use their single conversions column. Often fractional.
- Not: Kinetic orders. Platforms overlap (one buyer can be claimed by several), so never add conversions across platforms as if they were sales.

**Cost per conversion (`cost_per_conversion_usd`)**: spend ÷ platform-reported conversions. Not Kinetic's true acquisition cost, and not like-for-like across platforms (Meta counts purchases only).

**Reported ROAS (`reported_roas`)**
- Means: platform-reported conversion value ÷ spend.
- Not: true return on ad spend. Null for Meta (Meta reports no value). Null is not zero.

Ratios are computed from monthly totals, not averaged from daily ratios.

## Acquisition efficiency (`mart_acquisition_efficiency_monthly`, one row per month)

**Paid spend (`paid_spend_usd`)**: all six platforms combined.

**Blended CAC (`blended_cac_usd`)**
- Means: all paid spend ÷ first-time paying subscribers in the same month.
- Not: the cost of an ad-driven subscriber. It includes organic sign-ups in the divisor, so it overstates that cost, and it CANNOT be split by channel or campaign (no key links an ad to an order or subscriber). Spend and new payers are matched in the same month with no lag. Null means no new subscribers that month.

**Cumulative blended CAC (`cumulative_blended_cac_usd`)**: spend to date ÷ first-time subscribers to date. Use it for the trend: a month has only a handful of sign-ups, so single months swing widely.

The level (about $8.8k per subscriber overall) is a synthetic-data artifact, not a benchmark.

## Email and push (`mart_messaging_monthly`, one row per channel x campaign type x month)

The month is the month a message was SENT; opens and clicks arrive within 2 days. The unit is messages, not people.

**Sends / bounces / delivered (`sends`, `bounces`, `delivered`)**
- Means: messages sent; messages that bounced; sends minus bounces (there is no delivered event).
- Not: people reached. One person can receive many messages.

**Opens / clicks / unsubscribes (`opens`, `clicks`, `unsubscribes`)**
- Means: delivered messages that were opened; messages that were clicked (every click follows an open); messages after which the recipient unsubscribed. At most one of each per message.
- Not: a measure of interest or revenue. An open is a tracked event defined by this dataset; in real life email opens are inflated by privacy features, so compare channels and months, not outside benchmarks.

**Rates (`open_rate_fraction`, `click_rate_fraction`, `click_to_open_rate_fraction`, `unsubscribe_rate_fraction`, `bounce_rate_fraction`)**
- Means: opens / delivered, clicks / delivered, clicks / opens, unsubscribes / delivered, bounces / sends, as fractions (0.35 = 35%), computed from monthly totals.
- Not: attributable to revenue or subscribers. Nothing here links a message to an order. Triggered messages (sent after a customer action) open far more than broadcasts, so never average across campaign types without saying so. Null means a zero denominator.
- Late data: seven opens stamped 31 Jul to 1 Aug 2026 belong to 29-30 Jul sends and are counted in July. The latest month is cut off at the data's end.

## Web and app traffic (`mart_traffic_monthly`, one row per month x traffic source x landing page)

**Sessions (`sessions`)**
- Means: visits that started in the month, web and app.
- Not: people, and not sales. A session is one visit.

**Traffic source (`traffic_source`)**
- Means: for web sessions the UTM source on the link (meta, google_search, tiktok, youtube, dv360, snap, email); `untagged_web` for web sessions with no tag (direct, organic or untracked: the data cannot tell them apart); `app` for every app session (app sessions have no tags, landing page or referrer).
- Not: attribution. A session tagged meta arrived through a Meta-tagged link; no key links it to an ad, order or subscriber, so never credit revenue or subscribers to a source. UTM tags are URL tags, not ad-platform campaign IDs.

**Known / anonymous sessions (`known_sessions`, `anonymous_sessions`, `known_share_fraction`)**
- Means: sessions tied to a customer account (known at the time, or back-filled after the visitor signed up or logged in) versus anonymous web visitors. All app sessions are known.
- Not: a count of customers. Anonymous visitors are most of web traffic, and especially of paid traffic (about 95% anonymous).

**Average session length (`avg_session_seconds`)**
- Means: total session seconds / sessions.
- Not: engagement quality. App sessions run much longer than web sessions, so mix matters.

---

## Every mart: `data_through`
The latest date the data covers (2026-07-30). Later months are unknown, not zero.

## Not defined yet (say "I don't have this")
Churn rate, cohort retention, LTV, margin/profit, email or push performance at campaign level (only channel and campaign type exist), page-level or funnel metrics beyond landing page, and CAC or ROAS by channel or campaign.
