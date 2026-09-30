"""Run ONE read-only SQL statement against MotherDuck `kinetic` and print the rows.

Usage (from the repo root, with the dbt venv python):
    /Users/ben/.dbt-venv/bin/python scripts/md_select.py "select count(*) from information_schema.tables"
    /Users/ben/.dbt-venv/bin/python scripts/md_select.py --limit 50 "select * from dbt_dev_marts.mart_mrr_monthly"

Why it exists: project rule 4 says ad-hoc SQL against MotherDuck is SELECT-only. This
script enforces that in code, so it can be allowlisted in .claude/settings.json without
allowing arbitrary Python. It also loads MOTHERDUCK_TOKEN itself (from the environment, or
the `export MOTHERDUCK_TOKEN=` line in ~/.zshrc) and never prints it.

Accepted: a single statement starting with SELECT, WITH, FROM, DESCRIBE, SHOW, EXPLAIN or
SUMMARIZE. Anything containing a write/DDL/admin keyword is refused, even inside a longer
query (string literals are ignored when checking).
"""
import argparse
import os
import re
import sys

ALLOWED_START = ("select", "with", "from", "describe", "show", "explain", "summarize")
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|detach|copy|export|import|install|"
    r"load|pragma|set|reset|call|truncate|merge|replace|grant|revoke|vacuum|checkpoint|"
    r"use|begin|commit|rollback|read_text|read_csv|write_csv)\b",
    re.IGNORECASE,
)


def strip_literals(sql):
    """Blank out '...' string literals and comments so keywords inside them do not count."""
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def check(sql):
    body = strip_literals(sql).strip().rstrip(";").strip()
    if not body:
        return "empty statement"
    if ";" in body:
        return "only one statement is allowed"
    if not body.lower().startswith(ALLOWED_START):
        return "statement must start with one of: " + ", ".join(ALLOWED_START)
    hit = FORBIDDEN.search(body)
    if hit:
        return "refused keyword: " + hit.group(0).upper()
    return None


def load_token():
    if os.environ.get("MOTHERDUCK_TOKEN"):
        return
    try:
        with open(os.path.expanduser("~/.zshrc")) as f:
            for line in f:
                m = re.match(r"\s*export\s+MOTHERDUCK_TOKEN=(['\"]?)(.+?)\1\s*$", line, re.IGNORECASE)
                if m:
                    os.environ["MOTHERDUCK_TOKEN"] = m.group(2)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sql", help="one read-only SQL statement")
    ap.add_argument("--limit", type=int, default=200, help="max rows to print (default 200)")
    args = ap.parse_args()

    problem = check(args.sql)
    if problem:
        print("REFUSED: " + problem, file=sys.stderr)
        sys.exit(2)

    load_token()
    if not os.environ.get("MOTHERDUCK_TOKEN"):
        print("No MOTHERDUCK_TOKEN in the environment or ~/.zshrc", file=sys.stderr)
        sys.exit(3)

    import duckdb

    con = duckdb.connect("md:kinetic")
    cur = con.execute(args.sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchmany(args.limit + 1)
    print("\t".join(cols))
    for r in rows[: args.limit]:
        print("\t".join("" if v is None else str(v) for v in r))
    if len(rows) > args.limit:
        print("... truncated at %d rows (use --limit)" % args.limit, file=sys.stderr)


if __name__ == "__main__":
    main()
