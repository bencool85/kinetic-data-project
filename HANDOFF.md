# Handoff note (updated 2026-09-30; project now runs in Claude Code, daytime work on `master`)

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
- Phase 6 (semantic layer): DONE, confirmed by Ben 2026-09-30 (playbook section 13 updated and
  republished as artifact v26; LOG.md entry added).
  dbt/models/marts/_semantic_layer.yml (5 semantic models, 25 metrics) plus the calendar model
  metricflow_time_spine. `mf validate-configs` 0 errors; all 10 queries in
  docs/semantic_layer_validation.md match the hand-computed values. Full build 366/366 pass.
  MetricFlow 0.209 (dbt-metricflow 0.11.0) is installed in ~/.dbt-venv. Known limit (Ben accepted):
  only paid-media metrics have a second dimension (platform). Slicing subscribers/revenue (e.g. MRR by
  first-time vs returning) needs a new subscription-grain mart with a subscriber-type column: optional.
- Phase 7 (Skill): DONE, signed off by Ben 2026-09-30. docs/kinetic_skill.md (v1, renamed from _DRAFT):
  SQL on the marts is the default route, MetricFlow metrics where installed (dimension
  `platform_month__platform`). Quoted numbers re-checked against live data (incl. guest orders 33.7%).
  Ben's scope decisions: the Skill refuses churn rate, LTV, revenue by plan and email/push rates
  (no marts yet); it points at the dev schema `dbt_dev_marts`, to be swapped for a production
  schema before a real pilot (Phase 8).
  Still open for Phase 8: where the Skill file will live (.claude/skills/ vs claude.ai upload).
- Phase 8 (agents): NOT STARTED. Needs a pilot persona.
- Git: MERGED 2026-09-30. `overnight` was fast-forwarded into master and pushed by Ben (master and
  origin/master both at b0fcdca). New pattern: daytime work is on `master` (Claude commits locally,
  Ben pushes master). `overnight` is used only for unattended runs while Ben sleeps: before a run,
  Ben brings it up to date with master (`git checkout overnight && git merge --ff-only master`,
  then `git push origin overnight`); in the morning he reviews and merges it back into master
  himself. Claude's auto mode may block commits on master: if so, say it plainly and ask Ben.
- Playbook: section 13 ("Applied to Kinetic") is the single status list and matches this note. The
  published artifact was read from Claude Code on 2026-09-30; Claude Code has the Artifact tool and can
  republish to the same link, so no Cowork step is needed.

## Next step (start here)
0. Ben pushes `master` when ready (check `git log origin/master..master`). gh-pages was pushed.
1. Phase 8: choose a pilot persona, then scope one use case. Needs: a stable production schema for the
   marts, read-only access for the agent, guardrails doc, and a way to collect feedback.
2. Optional: subscription-grain mart to slice subscribers/revenue by subscriber type, channel or plan.
Recommend a model and ask Ben before starting each one (CLAUDE.md "Model and cost").

## Open decisions / to-dos
1. (Resolved 2026-09-30) Merge of `overnight` into master: done by Ben. Future overnight merges are his call.
2. Sharing the `kinetic` MotherDuck database with Ben's org: not done, needs his explicit yes.
3. Two-pager marketing sheet: Ben still owes a founder bio (About section) and a higher-resolution
   logo. Possibly a firm-domain email.
4. MotherDuck login: Ben added an `export MOTHERDUCK_TOKEN=...` line to ~/.zshrc himself
   (2026-09-30). A session started before that does not see it. For ad-hoc SQL use
   `scripts/md_select.py` (SELECT-only, loads the token itself, pre-approved in settings.json); for
   other commands load it with `eval "$(grep -i '^export motherduck_token=' ~/.zshrc | tail -1)"`.
   The token was partly shown in a screenshot in chat; Ben says he rotated it. Claude never prints
   or stores the token.
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
- Claude runs dbt, git and the manifest script itself, and commits each step. Manifest:
  `/Users/ben/.dbt-venv/bin/python generator/build_manifest.py` from the repo root (openpyxl is
  installed in the venv, not in the Mac's system python3; no HOME workaround needed). Pushes only
  `git push origin overnight`, only when told.
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
- MetricFlow: run `mf` from dbt/. Group by platform as `platform_month__platform`; filters use the
  template form, e.g. `--where "{{ TimeDimension('metric_time','year') }} = '2025-01-01'"`. Add
  `--decimals 2` to see cents. `month` cannot be used as an entity name (reserved word).
- Ben watches token use: short chats, new chat per phase.
