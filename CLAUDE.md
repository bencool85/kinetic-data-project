# Kinetic data-to-agents project (Claude Code instructions)

Ben (consultant, Double Black Solutions) is learning to build "data-to-agents"
foundations on a fully synthetic D2C fitness company, Kinetic. Same project as
the Cowork chats: this repo IS the shared memory. He is not a data engineer:
explain in plain language, with the why. Answer his questions before moving on.

## Start of every session
Read HANDOFF.md and the last 5 entries of CHANGELOG.md. Run `git branch --show-current`:
all Phase 3-5 work lives on branch `overnight`, NOT yet merged into master (merging is
Ben's call, never do it unasked). Work on `overnight` unless told otherwise.
Playbook (phases 0-8):
~/Documents/double-black-solutions/playbook/data-to-agents-playbook.html.
Decision log for the firm: ~/Documents/double-black-solutions/LOG.md.
Both are OUTSIDE this repo; start Claude Code with
`claude --add-dir ~/Documents/double-black-solutions` (settings.json also lists it).
MORNING_LIST.md is a record of the first overnight run only: ignore it unless debugging.

## The project
- 47 synthetic tables in MotherDuck database `kinetic`; dbt project in dbt/
  (staging -> intermediate -> marts; schemas dbt_dev_staging / _intermediate / _marts).
- Repo: github.com/bencool85/kinetic-data-project, branch master.
- Time series stop where the data stops (2026-07-30); NEVER use current_date.
- The dataset is STATIC for now (Ben, 2026-09-30): every series ends where the data ends;
  daily updates may come someday, not now.
- Ad-platform units: Meta BUDGETS are cents but Meta SPEND is already dollars (verified);
  Google/YouTube/DV360/Snap/TikTok are micros (BIGINT literals). Staging exposes `_usd`
  columns; use them, never re-convert. Google Search ad-group table is a rollup
  of keywords: never add both.

## Standing rules
1. One table or small group at a time. Hand-verify keys, joins, units against live
   data BEFORE writing the model; show validation results. No impossible scenarios.
2. Every added/changed file: add a line to generator/build_manifest.py and run
   `/Users/ben/.dbt-venv/bin/python generator/build_manifest.py` (the venv has openpyxl;
   the Mac's system python3 does not), add a CHANGELOG.md entry, keep it committed.
3. Commit each step yourself (end messages with the attribution lines your session
   gives you). Push ONLY `git push origin overnight`, and only when the task or Ben
   says so. Never push master, never force-push. Ben pushes master himself.
4. dbt: run from dbt/ with `/Users/ben/.dbt-venv/bin/dbt` (build, then read
   dbt/logs/dbt.log and dbt/target/run_results.json). MotherDuck writes happen ONLY
   through dbt into dbt_dev_* schemas. Never write to `main`, never drop/delete raw
   tables. Ad-hoc SQL against MotherDuck is SELECT-only (duckdb via the venv python,
   `md:kinetic`). Anything else needs Ben's OK.
5. Ask before deleting; otherwise `mv` into ~/Documents/kinetic-project/_to_delete/.
6. Decisions that are Ben's: interactive session -> ask with the question tool; unattended
   run -> take the recommended default and log it as "assumed, needs your call".
7. Before ending: update HANDOFF.md (status, open decisions, pitfalls) and commit.
8. Playbook (Ben wants to update it from HERE, not switch to Cowork):
   - Status changes go in section 13 ("Applied to Kinetic", `<section id="kinetic">`) and
     nothing else. Sections 00-12 are the framework: change them only with Ben's explicit
     approval (he approved principle 05 on 2026-09-30).
   - NEVER do a global string replace on row labels: section 12 (checklist) has rows with
     the same names as section 13. Slice the file by section id first, edit inside that
     slice, write it back.
   - Before editing: copy the file to /tmp/playbook_before.html. After: verify every other
     section is byte-identical to the backup (compare per section id) and show Ben that
     check.
   - Also add a dated entry to double-black-solutions/LOG.md, and keep HANDOFF.md in step.
   - Publishing: the readable playbook is the claude.ai artifact
     https://claude.ai/artifact/Fp9K8mpVyvbzvRvqxc1ruo. If you have the Artifact tool, read
     it first, then republish the edited file with `url` set to that link (same URL). If you
     do NOT have it, say so plainly, edit the local file, and write "playbook needs
     republish (Cowork)" in HANDOFF.md so the gap is visible.
   - A phase is marked done only after Ben confirms he understands it.
9. Never paste or store GitHub tokens. (Ben revoked the earlier ones on 2026-09-30; remind
   him again only if a new one is pasted.)
10. Docs site: the dbt docs are published from the `gh-pages` branch via GitHub Pages
    (https://bencool85.github.io/kinetic-data-project/). After model or description changes:
    `dbt docs generate` (from dbt/), then `bash scripts/rebuild_docs_branch.sh "message"`,
    then `git push origin gh-pages` (fast-forward only, never force).

## How to teach (Ben's rules from the Cowork chats)
- He is not a data engineer: plain language, the why behind each step, short replies with the
  outcome first, no recaps of what he just watched.
- Answer his questions before moving on. Do not advance a phase, or mark it done, until he
  confirms he understands it.
- Decisions that are his: ask with the question tool (multiple choice) in interactive sessions.

## Model and cost
Ben's call (2026-09-30): do NOT default to one model. At the start of each phase or task,
recommend which model to use (Opus, Sonnet or Haiku) and why, weighing quality against
cost, and ask Ben to confirm with the question tool before starting. Rule of thumb to base
the recommendation on: cheaper models for routine, mechanical work (renames, descriptions,
manifest/CHANGELOG upkeep); Opus for judgment calls (metric definitions, identity stitching,
semantic layer design, anything where a wrong answer is costly). Ben switches with /model.
Long chats are also expensive: suggest a new chat at phase boundaries.
