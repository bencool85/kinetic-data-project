# Handoff note (updated 2026-09-29, Phase 3 in progress)

Read this first in a new chat, then the last few CHANGELOG.md entries.

## Status
- Phase 0-1: 47-table synthetic dataset done, live in MotherDuck `kinetic`, 5-tab Dive built.
- Phase 2 (staging): COMPLETE. 47 of 47 raw tables have a `stg_kinetic__*` view; all built and tested in dbt.
- Built early (before their phase): `int_subscription_paid_periods`, `int_orders_refunded`, `mart_mrr_monthly`, `mart_storefront_revenue_monthly`. Reconcile these with the playbook when starting Phase 3/4.
- dbt now runs on Ben's Mac (dbt 1.10.23, venv ~/.dbt-venv, profile dbt/profiles.yml, output schemas dbt_dev_*). Staging built and 205/205 staging tests pass (2026-09-29). Intermediate (15/15) and marts (8/8) also built and tested in dbt. Ben runs dbt commands; Claude reads dbt/logs/dbt.log and dbt/target/run_results.json from the bridge.
- Git: see `git log`. Ben pushes himself (`cd ~/Documents/kinetic-project && git push`). Check `git log origin/master..HEAD` for unpushed commits and remind him.

## Next step (start here)
- Phase 3, model 2 of 5, `int_orders_net`: DONE (built and tested in dbt 2026-09-30, 16/16 pass; 3,650 rows, net $182,861.97). Playbook section 13 updated.
- Phase 3, model 3 of 5, `int_sessions_unified`: DONE (built and tested in dbt 2026-09-30, 14/14 pass; 49,895 rows, 340 back-filled). Playbook section 13 updated.
- Next: model 4 of 5, `int_messaging_events` (Braze email + push). Suggest a new chat.
- Remaining after that, in order: int_sessions_unified (back-fill via int_customer_identity), int_messaging_events (Braze email + push), int_paid_media_daily (needs Ben's call: which platform actions count as a "conversion").
- At the marts review: point mart_storefront_revenue_monthly at int_orders_net.paid_usd and rename its "gross_revenue_usd" (it is the paid amount).
- Pending Ben's yes: add a playbook principle "time series stop where the data stops; never extend to today". Check the Dive for the same current_date bug during the Phase 4 review.

## Open decisions / to-dos
1. RESOLVED 2026-09-29 (int_customer_identity): guest emails are matched to customer accounts by email (28 guest orders / 28 Braze guest addresses); anonymous web sessions are back-filled once a visitor signs up or logs in (340 sessions); deleted accounts are excluded.
2. Sharing the `kinetic` MotherDuck database with Ben's org: not done, needs his explicit yes.
3. Two-pager marketing sheet: Ben still owes a founder bio (About section) and a higher-resolution logo. Possibly a firm-domain email.
4. GitHub tokens (PATs) were pasted in chat earlier: remind Ben to revoke them.
5. Phase 3 onward per playbook: intermediate layer, marts, docs/descriptions, semantic layer, agent Skills.

## Decisions already made (do not reopen without reason)
- dbt output goes to its own schemas (profile `schema: dbt_dev` -> dbt_dev_staging / dbt_dev_intermediate / dbt_dev_marts), never `main`. Profile lives in dbt/profiles.yml. dbt is installed in a venv at ~/.dbt-venv on Ben's Mac. Ben approved dbt run writing these schemas (2026-09-29).
- Budgets: tables store the CURRENT budget; flight spend is capped at budget (fixed in generator, CSVs and live DB; audit Check 8 guards it).
- Ad-platform units: Meta cents; Google/YouTube/DV360/Snap/TikTok micros. Staging exposes `_usd` columns. `ctr` is a fraction (`ctr_fraction`).
- Google Search ad-group table is a rollup of the keyword table: never add them together.
- DV360 budget is monthly. TikTok has one budget column plus a mode flag (daily vs lifetime).
- Firm name: Double Black Solutions. Kinetic is left out of marketing collateral. See double-black-solutions/LOG.md.

## What Ben already understands (don't re-teach from scratch)
dbt (transformation tool run separately, not a database; models are SQL files; staging/intermediate/marts; views vs tables; source()/ref(); tests), the semantic layer vs marts, plain-language descriptions for agents, and "Skills". Also git basics: tarball, commit vs push, tokens. He learns best by asking questions while reading; answer them and do not move on until he confirms.

## Session setup to redo each time
- Work from the Data-to-Agents Playbook (~/Documents/double-black-solutions/playbook/data-to-agents-playbook.html, published at https://claude.ai/artifact/Fp9K8mpVyvbzvRvqxc1ruo). At the end of every sub-batch, update its section 13 (Applied to Kinetic) status table and "Next up", republish to the same URL, and add a line to double-black-solutions/LOG.md. Propose changes to the framework itself (sections 00-12) to Ben before making them. The playbook is not in git; the local file is the source of truth.
- Delete permission for ~/Documents is per session; ask only if needed (use mv to _to_delete otherwise).
- Ask before any MotherDuck write. Ben has approved writes case by case.
- Manifest: add a line in generator/build_manifest.py, then run with HOME="$HOME/mnt" python3 generator/build_manifest.py.
  When folders mount by name (no mnt/Documents), make a fake home: mkdir -p /tmp/fakehome/Documents && ln -sfn $HOME/mnt/kinetic-project /tmp/fakehome/Documents/kinetic-project (and double-black-solutions), then HOME=/tmp/fakehome python3 generator/build_manifest.py.

## Pitfalls that cost time before
- Time series must end at the last date the data covers (compute it from the data), never current_date: the synthetic data ends 2026-07-30, and months after that get invented numbers. Check the Dive and every new mart for this.
- Git commits from the bridge leave lock files (.git/HEAD.lock, objects/maintenance.lock, tmp_obj_*) when delete permission isn't granted, and the next commit fails. Ask for delete permission on kinetic-project at the start of any session that will commit; then remove only empty lock files and tmp_obj_* files.
- Do not run `git fetch` from the device bridge (left stale lock files).
- iCloud folders are unreadable from the bridge: keep everything in ~/Documents.
- Terminal cannot be typed into by Claude; Ben types git commands himself.
- MotherDuck integer overflow: use BIGINT literals when multiplying micros.
- Cloud sandbox files vanish between sessions; anything that matters must be committed to Ben's Mac.
- Ben watches token use: short chats, new chat per phase, Sonnet for routine work, Opus for judgment calls.
