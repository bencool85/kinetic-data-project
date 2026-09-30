#!/usr/bin/env bash
# Rebuild the gh-pages branch (the published dbt docs site) from dbt/target.
# Run AFTER `dbt docs generate`. Adds ONE commit on top of the existing gh-pages
# branch (so the push is a normal fast-forward, never a force push), without
# touching the working tree or the current branch. Ben (or an allowed
# `git push origin gh-pages`) publishes it. Usage: bash scripts/rebuild_docs_branch.sh "commit message"
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
MSG="${1:-dbt docs site rebuild}"
for f in index.html manifest.json catalog.json; do
  [ -f "dbt/target/$f" ] || { echo "dbt/target/$f missing: run dbt docs generate first"; exit 1; }
done
S="$(mktemp -d)"; IDX="$(mktemp -u)"
trap 'rm -rf "$S" "$IDX"' EXIT
cp dbt/target/index.html dbt/target/manifest.json dbt/target/catalog.json "$S/"
touch "$S/.nojekyll"
echo "Generated dbt docs site for the Kinetic project (synthetic data). Rebuilt by scripts/rebuild_docs_branch.sh." > "$S/README.md"
# Refuse to publish local paths or secrets.
if grep -lE "/Users/|motherduck_token|ghp_|github_pat_" "$S"/*.json "$S"/index.html >/dev/null 2>&1; then
  echo "Refusing: site files contain a local path or token-like string"; exit 1
fi
GD="$PWD/.git"
TREE=$(GIT_DIR="$GD" GIT_WORK_TREE="$S" GIT_INDEX_FILE="$IDX" bash -c 'git add -A && git write-tree')
PARENT=$(git rev-parse --verify -q refs/heads/gh-pages || true)
if [ -n "$PARENT" ] && [ "$(git rev-parse "$PARENT^{tree}")" = "$TREE" ]; then
  echo "gh-pages already matches dbt/target: nothing to do"; exit 0
fi
ARGS=(); [ -n "$PARENT" ] && ARGS=(-p "$PARENT")
NEW=$(git commit-tree "$TREE" "${ARGS[@]}" -m "$MSG")
git update-ref refs/heads/gh-pages "$NEW"
echo "gh-pages now at $(git rev-parse --short gh-pages). Publish with: git push origin gh-pages"
