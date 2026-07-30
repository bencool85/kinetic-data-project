"""
Builds/refreshes File_Manifest.xlsx at the project root — a running log of every
file committed to Ben's synced folder, with a description and last-updated timestamp.
Re-run this (with updated FILES list) any time files are added or edited.
"""
import os
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

PROJECT_ROOT = "/home/claude/kinetic-project"
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "File_Manifest.xlsx")

# (relative file path, category, description)
FILES = [
    ("README.md", "Docs", "Project overview and folder structure guide"),
    ("CHANGELOG.md", "Docs", "Plain-English log of every decision and build step"),
    ("docs/business_context.md", "Docs", "Kinetic business model: subscriptions, courses, merch, seasonality"),
    ("docs/schema_reference.md", "Docs", "Full 47-table schema reference across all domains"),
    ("docs/generation_plan.md", "Docs", "Build sequence, validation approach, canonical metrics, locked conventions"),
    ("generator/params.py", "Code", "Phase 0 Step 1: global constants (scale, dates, pricing, rates)"),
    ("generator/build_calendar.py", "Code", "Phase 0 Steps 2-3: builds seasonality calendar + channel mix schedule"),
    ("generator/build_manifest.py", "Code", "Builds/refreshes this file manifest spreadsheet"),
    ("internal/_sim_seasonality_calendar.csv", "Internal artifact", "Weekly demand multiplier driving signups/spend/traffic"),
    ("internal/_sim_channel_mix_schedule.csv", "Internal artifact", "Acquisition channel share over time (Meta/Google/YouTube/DV360/Snap/TikTok/organic)"),
    ("internal/seasonality_preview.png", "Chart", "Visual sanity-check of the seasonality calendar"),
    (".gitignore", "Repo config", "Excludes Python __pycache__ from git/sync"),
    ("File_Manifest.xlsx", "Docs", "This file — running log of every file committed to the folder"),
]


def last_modified_pacific(rel_path):
    import subprocess
    if rel_path == "File_Manifest.xlsx":
        # Self-referential: this file is about to be overwritten, so use "now"
        # rather than its stale pre-save mtime.
        result = subprocess.run(
            ["date", "+%Y-%m-%d %H:%M %Z"],
            env={**os.environ, "TZ": "America/Los_Angeles"},
            capture_output=True, text=True,
        )
        return result.stdout.strip()
    full_path = os.path.join(PROJECT_ROOT, rel_path)
    ts = os.path.getmtime(full_path)
    result = subprocess.run(
        ["date", "-d", f"@{int(ts)}", "+%Y-%m-%d %H:%M %Z"],
        env={**os.environ, "TZ": "America/Los_Angeles"},
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "File Manifest"

    headers = ["File Path", "Category", "Description", "Last Updated (Pacific)"]
    ws.append(headers)
    for col, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2A6F6F")
        cell.alignment = Alignment(vertical="center")

    for rel_path, category, description in FILES:
        timestamp = last_modified_pacific(rel_path)
        ws.append([rel_path, category, description, timestamp])

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")
            cell.alignment = Alignment(vertical="center", wrap_text=(cell.column == 3))

    widths = {1: 48, 2: 16, 3: 60, 4: 22}
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.freeze_panes = "A2"
    wb.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH} with {len(FILES)} file rows")


if __name__ == "__main__":
    build()
