# MORNING LIST (branch `overnight`)

## Progress
- Run 1 started 2026-09-30. Branch `overnight` created from master.
- Queue: 1 int_messaging_events [done] | 2 int_paid_media_daily [done] | 3 storefront mart cleanup [done] | 4 Phase 4 marts [3 of 3 done] | 5 Phase 5 descriptions [done] | 6 Phase 6 draft [done, DRAFT] | 7 Phase 7 draft [done, DRAFT]
- QUEUE COMPLETE (run 1, 2026-09-30). Later runs: write "nothing to do" and stop.

## 1. DO THESE FIRST

Nothing below has been run in dbt. Everything was hand-verified with equivalent SQL in MotherDuck only.

1. `cd ~/Documents/kinetic-project && git status` (you should be on branch `overnight`; if not, `git checkout overnight`)
2. `cd ~/Documents/kinetic-project/dbt && source ~/.dbt-venv/bin/activate && dbt parse` (checks the rewritten yml files first; if it errors, stop and tell me)
3. `dbt build --select int_subscription_data_through int_messaging_events int_paid_media_daily mart_mrr_monthly mart_storefront_revenue_monthly mart_subscriber_movement_monthly mart_paid_media_monthly mart_acquisition_efficiency_monthly`
4. Come back to chat and say "done" so the results can be checked from dbt/logs and MotherDuck.
5. `dbt docs generate` (Phase 5 descriptions are written; this builds the glossary site).
6. Push when you are happy: `cd ~/Documents/kinetic-project && git push -u origin overnight`. The branch is 10+ commits ahead of master (see `git log --oneline master..overnight`); master itself has 4 commits not yet pushed, and they go up with it. Nothing was committed to master.
7. Revoke any GitHub tokens (PATs) you pasted in earlier chats.

Note: `mart_storefront_revenue_monthly` renamed `gross_revenue_usd` to `paid_revenue_usd`. The Dive reads raw tables, not this mart, so it is unaffected.

## 2. Assumed decisions (need your call)

1. Paid-media "conversion": Meta = the `purchase` action only; Google Search, YouTube, DV360, Snap, TikTok = their single `conversions` column (no action types exist). Why: it is the most standard purchase-type outcome and avoids counting one shopper many times. Change: edit the `meta_purchases` filter or the per-platform CTEs in `int_paid_media_daily.sql`.
2. Meta has no conversion value column, so `conversions_value_usd` (and reported ROAS) is null for Meta. Change: none possible without new data.
3. Snap swipes count as clicks.
4. `int_messaging_events`: nothing de-duplicated; unique opens/clicks are for a future mart. Email events with no Braze customer are matched by email; Braze's own id wins on conflict.
5. Storefront mart: `gross_revenue_usd` renamed `paid_revenue_usd`; new `gross_before_discount_usd` and `discount_usd` columns. Change: rename in `mart_storefront_revenue_monthly.sql` and `_marts.yml`.
6. Blended CAC definition: all paid spend / FIRST-TIME paying subscribers (win-backs excluded), same-month matching, no lag. Change: `mart_acquisition_efficiency_monthly.sql`.
7. Subscriber movement uses end-of-month active counts (differs from MRR's 1st-of-month snapshot only when someone starts or cancels on the 1st; 8 of 35 months).
8. New `int_subscription_data_through` (the "where the data ends" rule) is now shared by `mart_mrr_monthly` and the movement mart. Same logic as before, moved.
9. Phase 4 mart choice: subscriber movement (CEO), paid media by platform (PMM/CMO), blended CAC (CEO/CFO). Left out: LTV, churn rate, cohort retention, channel CAC (no ad-to-order key; LTV needs a cohort design), revenue mix by stream, email funnel rates.
10. Phase 6: dbt Semantic Layer / MetricFlow (Kinetic has no BI tool). Drafts sit in `dbt/drafts/` so they cannot break `dbt build`.
11. yml files were rewritten with a script (formatting changed to block style; content and tests preserved, verified test-for-test).

## 3. Done (with plain-language explainers)

1. **int_messaging_events** (written, hand-verified, needs dbt build): all 36,232 Braze email and push events in one table. Email and push are different tables with different columns; this puts them side by side so a mart can count sends, opens and clicks across channels. Braze already says which customer got a message, except for emails to guest checkouts; for those we match the email address to an account when one exists (44 events). Judgment call: we keep every event as-is; "open rate" needs a decision about unique opens, so that is a later mart's job.
2. **int_paid_media_daily** (written, hand-verified, needs dbt build): one row per ad platform per day (6 x 1,095 rows), in dollars. Six platforms report at six different levels (per ad, per ad group, per exchange). This rolls each up to platform and day so they line up. Judgment calls: what counts as a "conversion" (see assumed #1), Google Search uses only the ad-group table (the keyword table is the same money), and gaps are not filled with zeros (none exist; a test guards it). Finding: raw Meta spend is in dollars, not cents as the project notes say.
3. **Storefront mart cleanup** (written, verified, needs dbt build): the storefront revenue mart now reads `int_orders_net` instead of redoing discount and refund maths, so that logic lives once. Its old "gross revenue" was really what customers paid, so it is renamed paid revenue, and a true gross (before discounts) column is added. All 36 months came out identical to the old mart.
4. **Phase 4 marts** (written, hand-validated, need dbt build):
   - `mart_subscriber_movement_monthly`: for each month, how many people started paying, how many stopped, and how many are paying at month end. 174 first-time + 25 win-backs, 101 churned, 98 paying at the end, which matches the Phase 0 figure of 98. Trials canceled before converting are not churn.
   - `mart_paid_media_monthly`: spend, clicks, conversions and ratios by platform by month. Ratios come from monthly totals, not averaged daily ratios. Conversions are the platforms' own claims.
   - `mart_acquisition_efficiency_monthly`: blended CAC = all ad spend / first-time paying subscribers. $8,802.91 overall (level is a synthetic artifact; spend dwarfs subscriber revenue). It cannot be split by channel because no key links ads to orders.
5. **Phase 5 descriptions** (written): a plain-language description on all 462 staging columns plus every intermediate and mart column, with caveats where a number could be misread. Enumerated values were checked against live data. Needs `dbt parse` then `dbt docs generate`.
6. **Phase 6 DRAFT** (unvalidated): `dbt/drafts/semantic_layer_DRAFT.yml` (5 semantic models, 25 metrics, each once) and `docs/semantic_layer_validation_DRAFT.md` (10 `mf query` checks with expected values). MRR-type snapshots are marked non-additive so they are never summed over months. Only paid-media metrics have two dimensions (platform, time). Extra morning steps to activate: build the marts; `pip install dbt-metricflow`; add a `metricflow_time_spine` model; move the file into `dbt/models/marts/`; `dbt parse`; `mf validate-configs`; run the 10 queries.
7. **Phase 7 DRAFT**: `docs/kinetic_skill_DRAFT.md`, which mart answers which question, every caveat as an instruction, and when to say "I don't have this data". Not reviewed by a data owner. Phase 8 not started (needs a live pilot persona).

## 4. Blocked / not started

- Nothing blocked. Phase 8 deliberately not started.
- Not validated overnight because dbt/MetricFlow cannot run here: every model, test, and the semantic layer draft.
- Possible next models: churn rate mart, cohort retention, email funnel mart (unique opens/clicks), LTV.
- Observations: 7 email events are stamped after the data end (latest 2026-08-01); 3 subscriptions start paying after 2026-07-30 (Aug 2026), excluded from marts.

## 5. Proposed playbook section 13 wording (true ONLY after your dbt build passes)

- Phase 3 status: "Built and tested in dbt: int_subscription_paid_periods, int_orders_refunded, int_customer_identity, int_orders_net, int_sessions_unified, int_messaging_events (36,232 email + push events), int_paid_media_daily (6 platforms x 1,095 days), int_subscription_data_through. Phase 3 exit check met: the storefront mart reads int_orders_net, so discount and refund logic lives once."
- Phase 4 status: "5 marts hand-validated and built: mart_mrr_monthly, mart_storefront_revenue_monthly, mart_subscriber_movement_monthly, mart_paid_media_monthly, mart_acquisition_efficiency_monthly."
- Phase 5 status: "Every model and column described in plain language with caveats; docs site generated." (only once `dbt docs generate` has run)
- Phase 6 status: "Draft metric definitions written (MetricFlow); not validated." Phase 7: "Draft Skill written; awaiting review." Phase 8: not started.
- Next up: "Confirm Phase 3-5 in dbt, review the Phase 6/7 drafts with Ben, then choose a pilot persona for Phase 8."
- Pending your yes (from HANDOFF): add the playbook principle "time series stop where the data stops; never extend to today".

## 6. Units running ahead of your understanding

Phases stay "awaiting your understanding" until you confirm. Everything above is ahead of that: int_messaging_events, int_paid_media_daily, the storefront mart change, the 3 new marts, Phase 5 descriptions, and the Phase 6 and 7 drafts. Suggested order to be walked through: paid-media conversion choice (assumed #1), then blended CAC (assumed #6), then the subscriber movement identity, then the drafts.
- Run 2 started 2026-09-30: QUEUE COMPLETE, nothing to do.
