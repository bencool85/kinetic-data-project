# Overnight plan (unattended run, written 2026-09-29 for a run at ~9 pm PT)

Ben is asleep. Work through the queue below with NO questions to him: where
a decision is his, take the recommended default, log it in MORNING_LIST.md as
"assumed, needs your call" (say how to change it), and keep going.

## Read first
HANDOFF.md, then the last 5 CHANGELOG.md entries, dbt/README.md, and the
Phase 3-5 sections of ~/Documents/double-black-solutions/playbook/data-to-agents-playbook.html.
Persona user stories: CHANGELOG.md entry "2026-08-14 -- Dive v2", docs/phase0_simulation_analysis.md, warehouse/kinetic_dive.tsx.

## Hard rules (Ben's standing rules; do not bend them)
1. Git: `git checkout -b overnight` from master (master must be clean; if the
   branch exists, check it out). ALL commits go on `overnight`. Never commit
   to master, never `git push`, never `git fetch`. Commit each step yourself,
   ending messages with the attribution lines your session gives you. If a
   commit fails on a lock file: delete permission is per session, so first
   call device_request_delete_permission for ~/Documents/kinetic-project; if
   it is not granted, `mv` only empty .lock files and tmp_obj_* into
   ~/Documents/kinetic-project/_to_delete/ and note it. If git says "Author
   identity unknown", use per-command `-c user.name="Ben" -c user.email="seeds_uptempo_0c@icloud.com"` (matches earlier commits); do not change git config.
2. MotherDuck: READ-ONLY (the query tool). Never call query_rw. Never delete anything.
3. dbt CANNOT run in this session (Ben's Mac only; you cannot type into Terminal).
   So every new model is written and HAND-VERIFIED by running its equivalent
   SQL against the existing dbt_dev_staging / dbt_dev_intermediate / dbt_dev_marts
   views in MotherDuck. A model that depends on a not-yet-built model must be
   verified by inlining that model's SQL as a CTE. Never claim a model is
   "built" or "tested in dbt". Say "written and hand-verified; needs dbt build".
4. Do NOT edit the playbook HTML or republish it overnight (its status table
   must only say things that are true). Put the proposed section 13 wording in
   MORNING_LIST.md instead. Do not edit the playbook's framework sections.
5. Per unit of work: hand-check against live data FIRST (keys, joins, units,
   no impossible scenarios: spend over budget, refund before purchase); write
   the model with a plain-language comment above the SQL explaining the why and
   each judgment call; add yml description + tests (test the grain); add a
   line to generator/build_manifest.py and run it (folders mount by name, so
   use the fake-home trick in HANDOFF.md); add a CHANGELOG entry; commit.
6. Time series stop where the data stops (data ends 2026-07-30); never use
   current_date. Ad-platform units: Meta cents; Google/YouTube/DV360/Snap/TikTok
   micros (use BIGINT literals); staging already exposes _usd columns.
   Google Search ad-group table is a rollup of the keyword table: never add both.
7. Ben is a consultant, not a data engineer: every unit gets a 3-5 sentence
   plain-language explainer (what it is, why it exists, the judgment calls) in
   MORNING_LIST.md so he can be walked through it. Phases stay "awaiting Ben's
   understanding" until he confirms.

## Queue (in order; stop at the end of the list or at any stop rule)
1. Phase 3, model 4 of 5: `int_messaging_events` (Braze email + push events in one shape, customer resolved via int_customer_identity where an email/id exists).
2. Phase 3, model 5 of 5: `int_paid_media_daily` (one row per platform per day, spend/impressions/clicks in USD, conversions). Decision assumed: pick the single most standard platform "purchase/conversion" action per platform, document each platform's mapping in the comment, log as assumed.
3. Phase 3 exit check: no business logic duplicated across two marts. Point
   mart_storefront_revenue_monthly at int_orders_net.paid_usd and rename its
   "gross_revenue_usd" to paid_revenue_usd (update yml and anything that reads it; grep first). Add gross (pre-discount) as a separate column.
4. Phase 4: up to 3 new marts, chosen from the persona user stories (CEO/CMO/CFO/PMM),
   not from what is easiest. One mart, one grain, unique test on the grain,
   hand-validate the number before writing dbt, `data_through` column if it is a time series.
5. Phase 5: plain-language `description:` on every model and column that lacks one (staging first, then intermediate, then marts), with an explicit caveat wherever a number could be misread. Writing only.
STOP after item 5. Do not start Phases 6-8.

## Stop rules
- A check fails twice on the same unit: revert that unit's uncommitted changes, log it in MORNING_LIST.md under "Blocked", move to the next unit.
- Device tools cannot reach the Mac: try the Projects tool `project_write` to write
  `overnight-status.md` saying so and the time; then stop.
- Never work past ~8 units of work total.
- Anything that would need Ben's approval (MotherDuck write, delete, push, a token): don't; list it.

## MORNING_LIST.md (create/append in the repo root, commit on the branch)
Sections, in this order:
1. DO THESE FIRST: the exact commands for Ben, in order:
   `cd ~/Documents/kinetic-project && git status` (you will be on branch `overnight`)
   `cd ~/Documents/kinetic-project/dbt && source ~/.dbt-venv/bin/activate && dbt build --select <every model added or changed overnight>`
   then "come back to chat and say done" so the results can be checked from dbt/logs and MotherDuck.
   Push (when he is happy): `cd ~/Documents/kinetic-project && git push -u origin overnight`. Say how many commits are on the branch ahead of master.
   `dbt docs generate` if Phase 5 descriptions were written.
   Remind him to revoke any GitHub tokens pasted in earlier chats.
2. Assumed decisions (each: what was assumed, why, how to change it).
3. Done: one line per unit + the plain-language explainer.
4. Blocked / not started, and why.
5. Proposed playbook section 13 wording (true only after his dbt build passes).
6. Units running ahead of his understanding.
Also update HANDOFF.md (status, open decisions, pitfalls) and commit it on `overnight`.
