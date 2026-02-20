#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/name_normalization.py

import csv
from pathlib import Path
from datetime import datetime

INTAKE_DIR = Path("docs/win/soccer/00_intake")
MAP_FILE = Path("mappings/soccer/team_map_soccer.csv")

NO_MAP_DIR = Path("mappings/soccer/no_map")
NO_MAP_DIR.mkdir(parents=True, exist_ok=True)
NO_MAP_FILE = NO_MAP_DIR / "no_map_soccer.csv"

ERROR_DIR = Path("docs/win/soccer/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "name_normalization_log.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# LOAD TEAM MAP (CASE INSENSITIVE)
# =========================

team_map = {}

if MAP_FILE.exists():
    with open(MAP_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (
                row["market"].strip().lower(),
                row["alias"].strip().lower(),
            )
            team_map[key] = row["canonical_team"].strip()
else:
    log("WARNING: team_map_soccer.csv not found")

unmapped = set()
files_processed = 0
rows_processed = 0
rows_updated = 0

# =========================
# PROCESS FILES
# =========================

for csv_file in INTAKE_DIR.rglob("*.csv"):
    files_processed += 1
    updated_rows = []
    modified = False

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            rows_processed += 1
            market = row.get("market", "").strip().lower()

            for side in ["home_team", "away_team"]:
                team = row.get(side, "").strip()
                key = (market, team.lower())

                if key in team_map:
                    canonical = team_map[key]
                    if row[side] != canonical:
                        row[side] = canonical
                        modified = True
                        rows_updated += 1
                else:
                    if team:
                        unmapped.add((market, team))

            updated_rows.append(row)

    if modified:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

# =========================
# WRITE UNMAPPED
# =========================

existing = set()

if NO_MAP_FILE.exists():
    with open(NO_MAP_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add((row["market"], row["team"]))

combined = existing.union(unmapped)

with open(NO_MAP_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["market", "team"])
    for market, team in sorted(combined):
        writer.writerow([market, team])

log(
    f"SUMMARY: files_processed={files_processed}, "
    f"rows_processed={rows_processed}, "
    f"rows_updated={rows_updated}, "
    f"unmapped_found={len(unmapped)}"
)

print("Name normalization complete.")
