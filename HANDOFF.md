# Handoff note (written 2026-09-29, end of Phase 2)

Read this first in a new chat, then the last few CHANGELOG.md entries.

## Status
- Phase 0-1: 47-table synthetic dataset done, live in MotherDuck `kinetic`, 5-tab Dive built.
- Phase 2 (staging): COMPLETE. 47 of 47 raw tables have a `stg_kinetic__*` view, with tests in `_kinetic__staging.yml`.
- Built early (before their phase): `int_subscription_paid_periods`, `int_orders_refunded`, `mart_mrr_monthly`, `mart_storefront_revenue_monthly`. Reconcile these with the playbook when starting Phase 3/4.
- NEVER RUN: `dbt run` / `dbt test`. dbt is not installed in Claude's environments and motherduck.com is blocked from them. Everything was validated by running equivalent SQL through the MotherDuck tools. First real dbt run must happen on Ben's Mac (pip install dbt-core dbt-duckdb; profile path 'md:kinetic') or dbt Cloud. Expect small fixes when it first runs.
- Git: last commit 605c34b. Ben pushes himself (`cd ~/Documents/kinetic-project && git push`). Check `git log origin/master..HEAD` for unpushed commits and remind him.

## Open decisions / to-dos
1. Braze stitching: Braze events use guest emails vs customer emails. How to match them is unresolved (Phase 3, needs Ben's call).
2. Sharing the `kinetic` MotherDuck database with Ben's org: not done, needs his explicit yes.
3. Two-pager marketing sheet: Ben still owes a founder bio (About section) and a higher-resolution logo. Possibly a firm-domain email.
4. GitHub tokens (PATs) were pasted in chat earlier: remind Ben to revoke them.
5. Phase 3 onward per playbook: intermediate layer, marts, docs/descriptions, semantic layer, agent Skills.

## Decisions already made (do not reopen without reason)
- Budgets: tables store the CURRENT budget; flight spend is capped at budget (fixed in generator, CSVs and live DB; audit Check 8 guards it).
- Ad-platform units: Meta cents; Google/YouTube/DV360/Snap/TikTok micros. Staging exposes `_usd` columns. `ctr` is a fraction (`ctr_fraction`).
- Google Search ad-group table is a rollup of the keyword table: never add them together.
- DV360 budget is monthly. TikTok has one budget column plus a mode flag (daily vs lifetime).
- Firm name: Double Black Solutions. Kinetic is left out of marketing collateral. See double-black-solutions/LOG.md.

## What Ben already understands (don't re-teach from scratch)
dbt (transformation tool run separately, not a database; models are SQL files; staging/intermediate/marts; views vs tables; source()/ref(); tests), the semantic layer vs marts, plain-language descriptions for agents, and "Skills". Also git basics: tarball, commit vs push, tokens. He learns best by asking questions while reading; answer them and do not move on until he confirms.

## Session setup to redo each time
- Delete permission for ~/Documents is per session; ask only if needed (use mv to _to_delete otherwise).
- Ask before any MotherDuck write. Ben has approved writes case by case.
- Manifest: add a line in generator/build_manifest.py, then run with HOME="$HOME/mnt" python3 generator/build_manifest.py.

## Pitfalls that cost time before
- Do not run `git fetch` from the device bridge (left stale lock files).
- iCloud folders are unreadable from the bridge: keep everything in ~/Documents.
- Terminal cannot be typed into by Claude; Ben types git commands himself.
- MotherDuck integer overflow: use BIGINT literals when multiplying micros.
- Cloud sandbox files vanish between sessions; anything that matters must be committed to Ben's Mac.
- Ben watches token use: short chats, new chat per phase, Sonnet for routine work, Opus for judgment calls.
