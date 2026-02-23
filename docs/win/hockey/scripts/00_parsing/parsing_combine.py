#!/usr/bin/env python3
# docs/win/hockey/scripts/00_parsing/parsing_combine.py

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/hockey/00_intake/predictions")
ERROR_DIR = Path("docs/win/hockey/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "parsing_combine.txt"

FIELDNAMES = [
    "league",
    "market",
    "game_date",
    "game_time",
    "home_team",
    "away_team",
    "home_prob",
    "away_prob",
    "away_projected_goals",
    "home_projected_goals",
    "total_projected_goals",
]

# =========================
# LOGGING
# =========================

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== parsing_combine run @ {datetime.utcnow().isoformat()} ===\n")

def log(msg: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# =========================
# COLLECT FILES
# =========================

files = list(INPUT_DIR.glob("hockey_*_*.csv"))

# If zero or one market file → nothing to combine
if len(files) <= 1:
    log("Combine skipped (0 or 1 market file present).")
    print("Combine skipped.")
    exit(0)

rows_by_date = defaultdict(list)
files_processed = 0
rows_processed = 0

for file_path in files:
    name = file_path.stem
    parts = name.split("_")

    if len(parts) < 5:
        continue

    date_key = "_".join(parts[1:4])

    try:
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not all(h in row for h in FIELDNAMES):
                    continue

                rows_by_date[date_key].append(row)
                rows_processed += 1

        files_processed += 1

    except Exception as e:
        log(f"Error reading {file_path.name}: {e}")

# If nothing valid found → skip safely
if not rows_by_date:
    log("No rows found to combine. Skipping.")
    print("No combine needed.")
    exit(0)

# =========================
# WRITE COMBINED FILES
# =========================

for date_key, rows in rows_by_date.items():
    outfile = INPUT_DIR / f"hockey_{date_key}.csv"

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    log(f"Wrote {outfile.name} ({len(rows)} rows)")

log(f"SUMMARY: files_processed={files_processed}, rows_processed={rows_processed}")
print("Combine complete.")
