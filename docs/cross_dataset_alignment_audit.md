# Cross-Dataset Alignment Audit

**Date:** 2026-08-13
**Scope:** Post-completion sweep across all 47 shipped Kinetic tables, run after the full dataset was built and every table's own 5-layer validator passed. Distinct from those per-table validators: this audit checks whether **aggregate** signals across tables agree with each other and with the shared seasonality calendar/channel-mix schedule, using correlation, growth-ratio, and volatility comparisons.
**Script:** `generator/audit_cross_dataset_alignment.py` (not part of the build/validate pipeline — run standalone).

## Bottom line

7 checks run. 6 passed clean. 1 check (#6) caught a real bug, which is now fixed and re-validated. 2 checks (#3, #5) surfaced genuine, explainable characteristics of the data that aren't bugs but are worth knowing about.

| # | Check | Result |
|---|-------|--------|
| 1 | Aggregate spend vs. aggregate demand | ✅ Pass |
| 2 | Channel mix consistency | ✅ Pass |
| 3 | Calendar-anchored events alignment | ✅ Pass (1 noted gap) |
| 4 | Long-run growth trend | ✅ Pass |
| 5 | Renewal/lag structure | ✅ Pass (1 noted characteristic) |
| 6 | Day-of-week / hour-of-day | 🔧 Bug found and fixed |
| 7 | Timezone/precision sweep | ✅ Pass |

---

## Check 1 — Aggregate marketing spend vs. aggregate demand

Total spend across all 6 ad platforms ($1,532,137 over 157 weeks) correlates positively with every aggregate demand signal it should plausibly drive:

- vs. total web_sessions: **r = 0.80**
- vs. new signups: **r = 0.66**
- vs. orders: **r = 0.49**
- vs. revenue: **r = 0.50**
- vs. the seasonality multiplier directly: **r = 0.97** (confirms spend really is formula-driven off the shared calendar)

No red flags — spend and demand move together at the aggregate level, with the correlation strength decreasing in a sensible order (sessions is the most direct/immediate effect, revenue the most indirect/lagged).

## Check 2 — Channel mix consistency

Stricter than each platform's own validator (which only checks a platform's spend against its *own* schedule share): this asks whether the **balance between platforms** in any given week tracks `_sim_channel_mix_schedule.csv`.

All 6 platforms' actual share-of-total-spend correlates positively with their expected share (r = 0.38 to 0.97), and every platform's whole-project average share is within ~0.5 percentage points of its intended share. Meta (r=0.89), Snap (r=0.91), and TikTok (r=0.97) track especially tightly; Google Search/YouTube/DV360 are noisier week-to-week (evergreen-only campaign structures, no flighted spikes to anchor the correlation) but still land close on average.

## Check 3 — Calendar-anchored events alignment

Every brand_lift flight (Meta/YouTube/Snap/TikTok), Braze "Seasonal Sale Promo" send, and seasonal discount code clusters correctly into either the BFCM/Holiday window or the New Year window — no independently-built seasonal moment drifted off-calendar.

**Noted gap (not a bug):** brand_lift flights ran in all 3 Novembers (2023, 2024, 2025), but `discount_codes.csv` only has a matching holiday code (`HOLIDAY2024`) and Braze send for **2024**. The 2023 and November-2025 brand-awareness flights ran with no accompanying promo code or Braze campaign. This is a legitimate real-world pattern (companies run brand awareness without always pairing it with a discount), but it's asymmetric across the 3 years and worth flagging in case you'd rather it be consistent. Left as-is pending your call — no data was changed for this.

**Resolved 2026-09-28:** Ben reviewed this and confirmed it should stay as-is -- real companies don't always pair brand-awareness spend with a promo code, so the asymmetry across the 3 Novembers is being kept as intentional, realistic variation rather than "fixed" for symmetry. No data changed. This closes the last open item from the original 47-table build.

## Check 4 — Long-run growth trend

`params.py`'s `GROWTH_END_MULTIPLIER = 2.4` is baked into the seasonality calendar. Quarterly growth ratios (avg of last 2 quarters / avg of first 2):

- seasonality multiplier: 1.59x
- signups: 1.39x
- ad spend: 1.53x
- orders: 4.29x
- revenue: 4.42x

Signups and spend track the calendar's growth rate closely (both are direct draws off the multiplier). Orders/revenue grow faster — expected, since the customer base compounds (repeat purchases from an accumulating subscriber pool on top of new signups), not a sign of drift.

Marketing efficiency (spend per signup) stays stable across all 11 quarters: **coefficient of variation = 0.11** — no systematic drift in acquisition cost over 3 years.

## Check 5 — Renewal/lag structure

Hypothesis going in: renewal invoice volume should echo new-subscription-start seasonality, but *smoothed* (a blend of many cohorts' billing cycles), so lower week-to-week volatility than fresh starts.

Results: renewals correlate with the seasonality multiplier about as strongly as fresh starts (r=0.37 vs 0.375), but **detrended volatility is actually higher for renewals (CV=0.70) than fresh starts (CV=0.52)** — the opposite of the hypothesis.

**Not a bug.** Explainable by: short average subscriber tenure and only 3 years of history limiting how much cohort-blending can smooth things out, plus annual-billing subscribers echoing their exact origin week a year later (which re-injects the *same* seasonal spikiness into renewals rather than smoothing it away). Documenting this as a real characteristic of the data rather than treating it as an error — no data was changed for this.

## Check 6 — Day-of-week / hour-of-day (bug found and fixed)

**Day-of-week:** confirmed uniform across every table checked (web_sessions, orders, app_sessions, meta_ad_insights_daily spend) — consistent with the design, which never modeled day-of-week weighting anywhere.

**Hour-of-day:** while checking this, found that all **38 `merch_to_sub_trigger` Braze email sends landed at exactly midnight (00:00:00)** — standing out against every other trigger type in the same table, which all draw a randomized business-hours delivery time. Root cause: that one code path in `build_braze_email_events.py` computed its send date by subtracting days from another timestamp, but never called the `_random_time_of_day()` helper every other trigger type uses — so it inherited a bare date (implicit midnight) instead of a randomized time.

**Fixed:** `merch_to_sub_trigger` now draws a random 6am–9pm send time like `trial_started`/`trial_ending`/`reactivation`. Rebuilt `data/braze_email_events.csv` (26,335 rows, up from 26,328 — the extra `rng` draws shift the shared random stream for every send generated afterward, so a handful of downstream open/click/bounce outcomes differ slightly even though the underlying rates are unchanged). Re-ran `validate_braze_email_events.py`: **13/13 passed.**

Also confirmed (not a bug): `web_sessions.started_at` hour-of-day is deliberately weighted to a 7am–11pm window (98.6% of sessions) — that's intentional in `build_web_sessions.py`, not an accidental gap.

## Check 7 — Timezone/precision sweep

Swept all 47 tables' 45 datetime columns and 34 date-only columns for formatting consistency: naive local timestamps (no timezone suffix, no UTC "Z", no offset), whole-second ISO 8601 precision, no mixed date/datetime formatting within a column.

**Result: zero exceptions across the entire dataset.** (One correction made along the way: the audit script's own timestamp-sniffing heuristic initially false-flagged unrelated numeric/text columns like phone numbers and state codes — fixed before trusting the result.)

---

## What changed as a result of this audit

- `generator/build_braze_email_events.py` — fixed `merch_to_sub_trigger` time-of-day generation.
- `data/braze_email_events.csv` — rebuilt (26,335 rows, 18,187 sends, unchanged send count).
- `generator/audit_cross_dataset_alignment.py` — new, added to `File_Manifest.xlsx`.
- `CHANGELOG.md`, `File_Manifest.xlsx` — updated.

No other shipped table was touched. Checks 3 and 5's findings are documented above but no data was changed for either — they're real characteristics of a synthetic dataset built this way, not defects, and I wanted your read on whether you'd like them addressed before touching anything.

## Check 8 — Spend vs. stored budget (added 2026-09-29)

None of the per-table validators ever compared a campaign's budget to what
it actually spent. Staging the paid-media tables surfaced that the original
build stored flat launch-era "typical day" budgets for all 3 years while
spend grew 2.4x, so later months spent far past them (TikTok up to ~20x) --
an impossible scenario on any real ad platform.

**Fixed.** Every always-on budget is now the campaign's *current* budget,
sized from realized spend: every calendar week averages at or under it
(Meta's weekly cap, stricter than Google's 30.4x monthly cap), no day above
1.75x (Meta's daily allowance; Google allows 2x), and DV360's monthly budget
covers its highest month. Only budget columns changed; spend untouched.

Holiday brand-lift flights had a separate, smaller problem: random daily
variation let 6 of 12 flights overshoot their lifetime budgets by 0.7-6.4%
($430 total). **Fixed** by capping each flight at its budget in the spend
generators (`paid_media_common.cap_flight_at_budget`), which only rescales
an overshooting flight's own days and leaves every other row identical.

Result after both fixes: 0 of 3,297 campaign-weeks over budget, 0 days
over 1.75x, 0 of 180 DV360 months over, all 12 flights at or under budget.
