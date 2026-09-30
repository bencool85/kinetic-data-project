#!/usr/bin/env bash
# Run `dbt` or `mf` (MetricFlow) from the dbt/ folder with MOTHERDUCK_TOKEN loaded, so no
# browser sign-in is needed. The token comes from the environment or the
# `export MOTHERDUCK_TOKEN=` line in ~/.zshrc and is never printed.
# Only these two tools are allowed, so this wrapper can be pre-approved in
# .claude/settings.json without allowing arbitrary commands.
# Usage (from the repo root):  bash scripts/md_env.sh dbt build --select mart_messaging_monthly
#                               bash scripts/md_env.sh mf validate-configs
set -euo pipefail
cd "$(git rev-parse --show-toplevel)/dbt"
if [ -z "${MOTHERDUCK_TOKEN:-}" ] && [ -f "$HOME/.zshrc" ]; then
  line="$(grep -i '^export motherduck_token=' "$HOME/.zshrc" | tail -1 || true)"
  [ -n "$line" ] && eval "$line"
  export MOTHERDUCK_TOKEN
fi
tool="${1:-}"; shift || true
case "$tool" in
  dbt) exec /Users/ben/.dbt-venv/bin/dbt "$@" ;;
  mf)  exec /Users/ben/.dbt-venv/bin/mf "$@" ;;
  *)   echo "md_env.sh: only 'dbt' and 'mf' are allowed (got '$tool')" >&2; exit 2 ;;
esac
