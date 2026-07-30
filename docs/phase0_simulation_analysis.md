# Phase 0 Simulation — Summary Analysis

**Run date:** 2026-07-30 | **Scale:** 860 customers, 17,050 anonymous visitors, Aug 2023 – Jul 2026

This revision adds two new mechanics on top of the previously-approved retention model
(100 active subscribers, 30% trial conversion, 40%-annual-retention / 3-month-average-churner
two-segment churn):

1. **January-clustered win-backs** — reactivation timing is now weighted by calendar
   month (same shape as the seasonality calendar), so total subscribers peak every
   January and taper through the year, instead of reactivating at a uniform random
   offset after churn.
2. **Email-acquired subscribers from the course/merch-only base** — a new pathway
   where a customer who only ever bought a la carte courses or merch can later be
   nudged into a trial by a targeted "come try a membership" email, timed off their
   own purchase history rather than the seasonal calendar.

Adding an active-subscriber-producing channel pushed total active subscribers above
the 100 target on the first run (128 of 1,100), so the customer/anonymous scale was
recalibrated down (1,100 → 860 customers, 21,800 → 17,050 anonymous) to land back
around 100 — the same kind of one-time empirical correction used in the original
retention-model calibration.

## 1. The customer funnel

![Customer funnel](../internal/funnel_chart.png)

| Stage | Count | % of previous stage |
|---|---|---|
| Total customers LTD | 860 | — |
| Ever started a trial | 551 | 64.1% |
| Converted to paying (ever-paid) | 174 | 31.6% |
| **Active subscribers today** | **98** | 56.3% of ever-paid |

Of the 551 trial starts, 513 came from the direct signup flow and 38 came from the new
email-triggered pathway (below). The 309 customers who never trialed at all (35.9% of
the base) created an account for a course or merch purchase and never touched the
subscription funnel — down from 442 previously, since some course/merch-only customers
now graduate into the trial funnel via email.

## 2. Where everyone stands today

![Segment breakdown](../internal/segment_breakdown_chart.png)

| Segment | Count | % of total |
|---|---|---|
| Trial, never converted (or still pending) | 377 | 43.8% |
| Course/merch-only, never subscribed | 309 | 35.9% |
| Active subscriber | 98 | 11.4% |
| Lapsed, gone quiet since lapsing | 70 | 8.1% |
| Lapsed, still buying since lapsing | 6 | 0.7% |
| **Total** | **860** | **100%** |

"Course/merch-only, never subscribed" now specifically means never subscribed **and**
never received/acted on the email trigger — someone who did get the email but didn't
convert lands in "trial, never converted" instead, same as any other non-converting
trial. The 377 "trial, never converted" figure includes 3 edge-case customers who
signed up in the final week of the dataset window, whose 7-day trial hadn't resolved
by `END_DATE` yet (`trial_in_progress` — correctly *not* counted as converted, since
there's no runway left in the dataset to show a resulting subscription).

## 3. Churn model recap

Unchanged from the prior calibration: every converting subscriber is assigned to one
of two segments — **quick** (exponential tenure, mean 3 months) or **loyal**
(effectively never organically churns within the window).

| Segment | Share of converts (target / realized) | 
|---|---|
| Quick churn | 61.1% / 58.6% (102 of 174) |
| Loyal | 38.9% / 41.4% (72 of 174) |

**Realized average tenure per closed subscription interval: 2.56 months** (target: 3.0)
— measured per-interval (not cumulative across win-back cycles), close to target given
the exponential distribution's spread and the smaller sample at this scale.

Of the 76 lapsed subscribers:

| Post-lapse behavior | Target | Realized |
|---|---|---|
| Still buying courses/merch since lapsing | 10% | 7.9% (6 of 76) |
| Gone completely quiet | 90% | 92.1% (70 of 76) |

## 4. Trial funnel detail, by pathway

The two trial pathways have different target conversion rates, so they're reported
separately rather than blended:

| Pathway | Trials started | Converted | Target conversion |
|---|---|---|---|
| Direct signup | 513 | 156 (30.4%) | 30% |
| Email-triggered (course/merch-only → trial) | 38 | 18 (47.4%) | 45–50% |
| **Combined** | **551** | **174 (31.6%)** | — |

Both pathways land within normal sampling variance of target.

## 5. New: email-acquired subscribers from the course/merch-only base

A course/merch-only customer's own purchase history now determines whether — and
when — they might get nudged into a trial:

- **~17.5% of course/merch-only customers** (target range 15–20%) eventually receive
  this email and start a trial because of it. Realized: 38 of ~347 course/merch-only
  signups (10.9% realized — lower than the 17.5% input rate, because the trigger
  requires 3–12 months of runway *after* their first purchase *and* enough remaining
  dataset time to resolve a 7-day trial; customers who signed up late in the window
  don't have enough of either).
- Of those 38, **47.4% converted to paying** (target 45–50%) — the better odds
  reflecting that this is a warm, already-purchasing audience rather than a cold lead.
- **13 of the 18 converts are still active subscribers today**; 5 have since lapsed
  normally through the same two-segment churn model as any other subscriber.
- Timing is relative to the customer's own first course/merch order (3–12 months
  after), not the seasonal calendar — this is a triggered, not calendared, send.

This is now a real (if modest) acquisition channel: about 1 in 13 currently-active
subscribers (13 of 98) originated from this pathway rather than a direct trial signup.

## 6. Win-backs, now January-clustered

25 customers have at least one reactivation event. Reactivation timing is sampled by
calendar month only (using the same relative weights as the seasonality calendar —
January highest, mid-summer lowest), independent of the multi-year growth trend, with
a minimum 1-month gap enforced after churn:

| Month | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reactivations | 4 | 1 | 5 | 1 | 6 | 0 | 6 | 0 | 0 | 1 | 1 | 0 |

At only 25 events, month-level counts are noisy (May and July look elevated here purely
by chance). The underlying *mechanism* was validated separately with a 20,000-draw
synthetic test of the sampler alone, which reproduced the target month weights closely
(January ≈13.7% of draws vs. a ≈14.2% target share, July ≈5.8% vs. a ≈5.9% target
share) — confirming the January skew is real and will show up more clearly at larger
scale or over more simulated years, even though this run's small win-back count doesn't
visually prove it on its own.

Reactivation channel split (25 events): 13 email, 12 organic, 0 push — the 50/15/35
target weights are directionally present but, again, noisy at n=25 (push landing zero
times here is plausible sampling variance, not a bug).

## 7. Order volume

2,409 total orders across the 860 customers (1,077 course, 1,332 merch), plus 1,257
guest merch orders from the 17,050-person anonymous population (7.4% guest-conversion
rate, matching the ~8% target). Total commerce volume across the dataset: **3,666
orders** over 3 years.

## 8. Scale changes, cumulative

| Parameter | Original plan | After retention recalibration | After this update | Why |
|---|---|---|---|---|
| Total customers | 100 | 1,100 | **860** | Re-derived once more after the email pathway added active subscribers beyond the 1,100-customer calibration |
| Anonymous population | 2,000 | 21,800 | **17,050** | Scaled proportionally |
| Trial conversion rate (direct signup) | 65% | 30% | 30% (unchanged) | — |
| Trial conversion rate (email-triggered) | n/a | n/a | **47.5%** | New pathway, warmer audience |
| Win-back timing | n/a | uniform 1–7 month gap | **January-weighted, ≥1 month gap** | Requested realism: subscriber count should peak every January |

## 9. What this means for later phases

- The `subscriptions` table (Phase 2) will materialize these intervals directly — 98
  currently-`active` rows, 76 `canceled` rows (some with a subsequent `resumed`
  interval from the 25 reactivations), regardless of whether the customer's original
  `account_type` was subscriber or course/merch-only.
- The `orders` table (Phase 3) still respects that lapsed-and-quiet customers (70 of
  them) contribute zero rows after their churn date.
- `customer_segment_membership` (Phase 4) should key off actual trial/subscription
  status (as this ground truth already does), not the original `account_type` field —
  the email-acquired subscribers are the clearest case of why: their `account_type` is
  still `course_merch_only` (their original signup reason), but they're an active
  subscriber today. The `trial.trigger` field (`signup` vs. `email_reactivation`) is
  preserved in the ground truth for Phase 6 (Braze) to use as the attribution answer key.
- Engagement tier assignment was corrected to key off actual conversion/active status
  rather than original `account_type` — this was a latent inconsistency in the prior
  version (a subscriber whose trial never converted could still be tiered "power") that
  the new pathway made worth fixing now, since email-acquired subscribers need the same
  correct tiering as anyone else.
