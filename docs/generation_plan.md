# Generation Plan

## Core principle

Generating 47 tables independently and reconciling afterward doesn't work — instead,
build a **single shared ground-truth timeline per customer first** (Phase 0, internal
only), and derive every shipped table from it. Impossible cross-table scenarios (a
course purchase during an active subscription, an email before signup) are prevented
by construction, not caught after the fact.

## Build sequence (dependency-ordered)

| Phase | Tables | Depends on |
|---|---|---|
| 0 | *(internal only)* master timeline, anonymous population, seasonality calendar | — |
| 1 | customers, customer_addresses, devices, identity_map, products, product_variants, subscription_plans, segments (definitions) | Phase 0 |
| 2 | subscriptions, subscription_events, invoices | Phase 1 |
| 3 | orders, order_line_items, payments, refunds, discount_codes | Phase 2 (enforces "no course purchase while subscribed") |
| 4 | customer_segment_membership | Phase 2–3 (membership computed from real behavior) |
| 5 | web_sessions, web_events, app_sessions, app_events | Phase 1 identity_map/devices; should line up with Phase 3 orders |
| 6 | braze_email_campaigns/events, braze_push_campaigns/events | Phase 1 customers/segments |
| 7 | All 6 paid-media platforms | Shared seasonality calendar |

## Validation

After **every single table**: cumulative check suite (load into local DuckDB, run as
SQL), layered:
1. Structural (required fields non-null, valid enums/dates)
2. Referential integrity (every FK resolves, except intentionally nullable ones)
3. Temporal ordering (event timestamp ≥ referenced entity's creation timestamp)
4. Business-rule invariants (no course order during active subscription; guest
   checkout only on merch; refund ≤ order total; subscription_events sequence valid)
5. Distributional sanity (guest-checkout rate, trial-conversion rate, etc. in expected
   ranges)

Short pass/fail summary shown after each table, not raw query output.

## Master timeline contents (per customer)

signup_date, signup_source (true first-touch channel), trial_start/end/outcome,
subscription intervals (plan/status/start/end), churn_date, order events
(type/date/amount), engagement_tier, pre-signup anonymous_id(s).

## Debug artifacts (internal, not part of the 47 shipped tables)

- `_sim_customer_timeline.json` — full nested ground truth
- `_sim_customer_timeline_summary.csv` — flattened, human-readable
- `_sim_seasonality_calendar.csv` — date-indexed demand multipliers
- `_sim_attribution_ground_truth.json` — the *true* channel/campaign behind each
  session/customer, kept separately since shipped UTM data is intentionally imperfect
  (lets us grade AI-agent attribution answers later)
- `_sim_anonymous_population.csv` — ~2,000 never-converting visitors, some of whom
  make guest merch purchases without ever getting a customer_id

## Canonical metrics — pressure-tested, all derivable

MRR/ARR, active subscribers, trial conversion, churn (voluntary/involuntary), upgrade/
downgrade revenue, course/merch revenue & AOV, guest checkout rate, refund rate,
discount redemption, course attach rate, customer LTV (customer-scoped only — guests
excluded, by design), segment-level LTV/churn, cohort retention, email/push funnel
metrics, app/web engagement, CAC/ROAS by channel, retargeting effectiveness.

## Five conventions locked for Phase 0

1. `customers.signup_source` derived from the simulated true first touch, not assigned
   independently
2. `web_sessions` UTM convention: `utm_source` cleanly names the channel; `utm_campaign`
   only loosely matches real ad-platform campaign names (clean channel-level
   attribution, realistically fuzzy campaign-level attribution)
3. `utm_source` includes `email`/`push` values for Braze-driven sessions
4. One shared `anonymous_id` namespace across web_sessions, anonymous-grain segments,
   and ad-platform `targeting_segment_id` links
5. Fitness-specific event vocabulary for app_events/web_events (workout_completed,
   class_started, streak_achieved, etc.)

## Open default assumptions (flag if you want these changed)

- Trial conversion rate ~65%
- Ever-subscribe vs. course/merch-only-account split ~60/40
- Basic/Plus split among subscribers ~75/25
- Anonymous "ghost" population size ~2,000
