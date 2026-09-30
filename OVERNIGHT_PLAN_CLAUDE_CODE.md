# Overnight plan, Claude Code version

Same queue, stop rules, Resume protocol and MORNING_LIST.md format as
OVERNIGHT_PLAN.md, EXCEPT (this file overrides that one; CLAUDE.md rules apply):
- dbt CAN run here. After hand-verifying a unit, run
  `/Users/ben/.dbt-venv/bin/dbt build --select <model>` from dbt/, read
  dbt/logs/dbt.log + dbt/target/run_results.json, then check row counts in MotherDuck.
  Only say "built and tested in dbt" when the build passed. A failure twice on
  one unit = revert it and log it under Blocked.
- After each unit that passes, `git push origin overnight` (never master, never force).
  Push failure: log it in MORNING_LIST.md and carry on.
- No Cowork-only steps: no project_write, no playbook republish (log it in HANDOFF.md).
- Morning list: replace "run dbt build" with the results you already have; list only what
  Ben must do (review, merge overnight into master, republish playbook from Cowork,
  decisions assumed, revoke tokens).
