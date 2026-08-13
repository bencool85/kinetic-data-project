"""
Loads all 47 Kinetic CSV tables into a MotherDuck database, one table per CSV,
named after the file (orders.csv -> table `orders`, etc.).

IMPORTANT: run this on YOUR OWN machine, not inside a Claude Cowork session --
MotherDuck needs outbound internet access that the Cowork cloud sandbox
doesn't have. This script expects to live in a `warehouse/` folder sitting
right next to `data/` (i.e. the same layout as the synced project folder in
your iCloud Drive) -- it finds data/ automatically from its own location, so
you can run it from anywhere as long as that folder structure is intact.

--- One-time setup ---
1. Install duckdb:
       pip install duckdb
   (or `pip install --upgrade duckdb` if you already have an old version --
   MotherDuck currently requires a fairly recent client, roughly 1.4.x+.)

2. Create a free MotherDuck account (no credit card needed):
       https://app.motherduck.com/?auth_flow=signup

3. Create an access token:
       app.motherduck.com -> click your org name (top left) -> Settings
       -> "+ Create token" -> name it (e.g. "kinetic-loader") -> copy it

4. Put the token in your shell environment (don't hardcode it in this file):
       export motherduck_token='paste-your-token-here'
   Add that line to your ~/.zprofile or ~/.bash_profile so it persists
   across terminal sessions.

--- Run it ---
    python3 warehouse/load_to_motherduck.py

This creates (or reuses) a MotherDuck database called `kinetic`, loads all
47 tables, and prints a row-count verification for each one (MotherDuck vs.
the source CSV) so you can confirm nothing got dropped or duplicated during
the load -- the same "validate every table" discipline used to build this
dataset in the first place.
"""
import os
import re
import sys
from pathlib import Path

import duckdb

DATABASE_NAME = "kinetic"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load_dotenv(path):
    """Tiny manual .env loader (KEY=value per line) -- avoids adding a
    python-dotenv dependency just for one optional file. Only sets a var if
    it isn't already present in the environment, so an explicit `export`
    always wins over the .env file. NEVER commit this .env file to git --
    it holds a live MotherDuck access token; it's already excluded via
    .gitignore."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def main():
    _load_dotenv(ENV_FILE)

    if not os.environ.get("motherduck_token"):
        sys.exit(
            "ERROR: motherduck_token environment variable is not set.\n"
            "Get a token at app.motherduck.com -> Settings -> Create token, then run:\n"
            "  export motherduck_token='<your token>'\n"
            "(or drop it into a warehouse/.env file as motherduck_token=<token> --\n"
            "that file is gitignored and never gets committed or synced automatically)."
        )

    if not DATA_DIR.is_dir():
        sys.exit(f"ERROR: expected a data/ folder at {DATA_DIR} -- keep this script's "
                  f"warehouse/ folder next to data/, or edit DATA_DIR above.")

    csv_paths = sorted(DATA_DIR.glob("*.csv"))
    if not csv_paths:
        sys.exit(f"No CSV files found in {DATA_DIR}")

    print(f"Found {len(csv_paths)} CSV files in {DATA_DIR}")
    print(f"Connecting to MotherDuck, database '{DATABASE_NAME}' ...")
    con = duckdb.connect(f"md:{DATABASE_NAME}")

    loaded = []
    for path in csv_paths:
        table_name = re.sub(r"\W", "_", path.stem)
        with open(path, "r", encoding="utf-8") as f:
            local_rows = sum(1 for _ in f) - 1  # minus header row

        # sample_size=-1 scans the WHOLE file for type inference rather than
        # duckdb's default first-20,480-row sample -- worth the extra
        # runtime at this dataset's small size (41MB total) to avoid a
        # column silently getting mistyped from a value that only shows up
        # deep in a larger file like web_events.csv.
        con.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS
            SELECT * FROM read_csv('{path.as_posix()}', header = true, sample_size = -1)
        """)
        remote_rows = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        status = "OK" if remote_rows == local_rows else "MISMATCH"
        print(f"  [{status}] {table_name:45s} {remote_rows:>7,} rows  (source CSV: {local_rows:,})")
        loaded.append((table_name, remote_rows, local_rows))

    mismatches = [t for t in loaded if t[1] != t[2]]
    print(f"\n{len(loaded)} tables loaded into MotherDuck database '{DATABASE_NAME}'.")
    if mismatches:
        print(f"WARNING: {len(mismatches)} table(s) have a row-count mismatch -- check these:")
        for name, remote, local in mismatches:
            print(f"  {name}: MotherDuck={remote} vs. source CSV={local}")
    else:
        print("All row counts match their source CSVs exactly -- clean load.")

    print(f"\nBrowse it at https://app.motherduck.com -> database '{DATABASE_NAME}'")


if __name__ == "__main__":
    main()
