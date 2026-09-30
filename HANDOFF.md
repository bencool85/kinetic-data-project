# Handoff note (updated 2026-09-30; project now runs in Claude Code, branch `overnight`)

Read this first in a new chat, then the last 5 CHANGELOG.md entries. CLAUDE.md holds the
standing rules; this note holds status, open decisions and pitfalls.

## Status
- Phase 0-1: DONE. 47-table synthetic dataset live in MotherDuck `kinetic`, 5-tab Dive built.
- Phase 2 (staging): DONE. 47 of 47 raw tables have a `stg_kinetic__*` view; 205/205 staging tests pass.
- Phase 3 (intermediate): DONE, confirmed by Ben 2026-09-30. Eight models: int_subscription_paid_periods,
  int_orders_refunded, int_customer_identity, int_orders_net, int_sessions_unified, int_messaging_events,
  int_paid_media_daily, int_subscription_data_through.
- Phase 4 (marts): DONE, confirmed by Ben 2026-09-30. Five marts: mart_mrr_monthly,
  mart_storefront_revenue_monthly, mart_subscriber_movement_monthly, mart_paid_media_monthly,
  mart_acquisition_efficiency_monthly. Last full build: 66/66 pass (2026-09-30).
  Not built (no mart yet): churn rate, cohort retention, LTV, email funnel rates.
- Phase 5 (documentation): DONE, confirmed by Ben 2026-09-30. Description on every model and column;
  docs site at https://bencool85.github.io/kinetic-data-project/ (gh-pages branch, a snapshot of the
  2026-09-30 build: rebuild after model changes, CLAUDE.md rule 10); glossary at docs/metrics_glossary.md.
- Phase 6 (semantic layer): DRAFT ONLY, not validated. dbt/drafts/semantic_layer_DRAFT.yml (5 semantic
  models, 25 metrics) and docs/semantic_layer_validation_DRAFT.md (10 checks with expected values).
- Phase 7 (Skill): DRAFT ONLY, needs Ben's review. docs/kinetic_skill_DRAFT.md. Not to be used until
  Phase 6 is validated.
- Phase 8 (agents): NOT STARTED. Needs a pilot persona.
- Git: all Phase 3-5 work is on branch `overnight`, pushed to origin/overnight and in sync (2026-09-30).
  `overnight` is 23 commits ahead of master and NOT merged: merging is Ben's call, and Ben pushes master.
- Playbook: section 13 ("Applied to Kinetic") is the single status list and matches this note. The
  published artifact was read from Claude Code on 2026-09-30; Claude Code has the Artifact tool and can
  republish to the same link, so no Cowork step is needed.

## Next step (start here)
1. Phase 6 validation: `pip install dbt-metricflow` into ~/.dbt-venv, add a `metricflow_time_spine`
   model, move the draft yml from dbt/drafts/ into dbt/models/marts/, run `dbt parse` and
   `mf validate-configs`, then run the 10 queries in docs/semantic_layer_validation_DRAFT.md and compare
   with the expected values. Known limit: only paid-media metrics have a second dimension (platform),
   so the playbook's exit test (2 dimensions) is met for those only.
2. Phase 7: Ben reviews the draft Skill.
3. Phase 8: choose a pilot persona, then scope one use case.
Recommend a model and ask Ben before starting each one (CLAUDE.md "Model and cost").

## Open decisions / to-dos
1. Merging `overnight` into master: not done, Ben's call.
2. Sharing the `kinetic` MotherDuck database with Ben's org: not done, needs his explicit yes.
3. Two-pager marketing sheet: Ben still owes a founder bio (About section) and a higher-resolution
   logo. Possibly a firm-domain email.
4. MotherDuck login: no token is saved on the Mac, so dbt opens a browser login when it connects
   (seen with `dbt debug`, 2026-09-30). Optional fix, Ben's to do himself: set a `motherduck_token`
   environment variable. Claude never handles or stores the token.
5. The Cowork Project instructions (claude.ai) still contain the old MODEL & COST line; Ben edits
   those in the Project settings if he keeps using Cowork.
6. `_to_delete/` holds four old git lock files from the Cowork runs (run3*_HEAD.lock, run3*_index.lock);
   safe to delete once Ben says so.

## Decisions already made (do not reopen without reason)
- dbt output goes to its own schemas (profile `schema: dbt_dev` -> dbt_dev_staging /
  dbt_dev_intermediate / dbt_dev_marts), never `main`. Profile lives in dbt/profiles.yml; dbt 1.10 is
  installed in the venv ~/.dbt-venv.
- Identity (int_customer_identity, 2026-09-29): guest emails are matched to customer accounts by email
  (28 guest orders / 28 Braze guest addresses); anonymous web sessions are back-filled once a visitor
  signs up or logs in (340 sessions); deleted accounts are excluded.
- Paid-media "conversion" = Meta purchase action only; other platforms use their single conversions
  column. CAC is blended only: it cannot be split by channel because no ad-to-order key exists.
- Budgets: tables store the CURRENT budget; flight spend is capped at budget (fixed in generator, CSVs
  and live DB; audit Check 8 guards it).
- Ad-platform units: Meta BUDGETS are cents, Meta SPEND is already dollars (verified 2026-09-30);
  Google/YouTube/DV360/Snap/TikTok are micros. Staging exposes `_usd` columns. `ctr` is a fraction
  (`ctr_fraction`).
- Google Search ad-group table is a rollup of the keyword table: never add them together.
- DV360 budget is monthly. TikTok has one budget column plus a mode flag (daily vs lifetime).
- Playbook principle 05 "time series end where the data ends" added with Ben's approval (2026-09-30).
  Kinetic stays a STATIC dataset for now (ends 2026-07-30); daily updates may come someday.
- Model: no fixed default (Ben, 2026-09-30). Recommend per phase or task and ask Ben to confirm.
- Ben keeps Claude Code's auto permission mode on; the CLAUDE.md rules and the settings.json deny
  rules still apply.
- GitHub tokens pasted in earlier chats were revoked by Ben (2026-09-30).
- Firm name: Double Black Solutions. Kinetic is left out of marketing collateral. See
  double-black-solutions/LOG.md.
- MORNING_LIST.md is a record of the first overnight run only; its open items live in playbook
  section 13.

## What Ben already understands (don't re-teach from scratch)
dbt (transformation tool run separately, not a database; models are SQL files;
staging/intermediate/marts; views vs tables; source()/ref(); tests), the semantic layer vs marts,
plain-language descriptions for agents, and "Skills". Also git basics: tarball, commit vs push, tokens.
He learns best by asking questions while reading; answer them and do not move on until he confirms.

## How work runs in Claude Code (replaces the Cowork-era setup notes)
- Claude runs dbt, git and the manifest script itself (`python3 generator/build_manifest.py`, no HOME
  workaround needed), and commits each step. Pushes only `git push origin overnight`, only when told.
- MotherDuck: writes only through dbt into dbt_dev_* schemas; ad-hoc SQL is SELECT-only.
- Playbook: at the end of every sub-batch, update section 13 and "Next up" following CLAUDE.md rule 8
  (backup, edit inside the section-13 slice, per-section unchanged check shown to Ben), republish to
  https://claude.ai/artifact/Fp9K8mpVyvbzvRvqxc1ruo, and add a line to double-black-solutions/LOG.md.
  The playbook is not in git; the local file is the source of truth. Editing it from Claude Code is
  allowed by settings.json but has not been exercised yet: the first update is the real test.
- The Cowork-only pitfalls (device-bridge lock files, fake HOME, unreadable iCloud folders, sandbox
  files vanishing) were removed from this note on 2026-09-30; they are in git history if needed.

## Pitfalls that cost time before
- Time series must end at the last date the data covers (compute it from the data), never
  current_date: the synthetic data ends 2026-07-30, and months after that get invented numbers. Check
  the Dive and every new mart for this.
- Seven Braze email events are stamped after the data end (2026-07-30), and 3 subscriptions start
  paying in Aug 2026: both are excluded from the marts.
- MotherDuck integer overflow: use BIGINT literals when multiplying micros.
- Older notes say "Meta cents": only Meta BUDGETS are cents, spend is dollars.
- The semantic-layer draft lives in dbt/drafts/ (outside model-paths) on purpose, so an unvalidated
  file cannot break `dbt build`. Move it only as part of Phase 6 validation.
- Ben watches token use: short chats, new chat per phase.
