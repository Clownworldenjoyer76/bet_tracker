#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/name_normalization.py

import csv
from pathlib import Path

# =========================
# PATHS
# =========================

INTAKE_DIR = Path("docs/win/soccer/00_intake")
MAP_FILE = Path("mappings/soccer/team_map_soccer.csv")
NO_MAP_DIR = Path("mappings/soccer/no_map")
NO_MAP_FILE = NO_MAP_DIR / "no_map_soccer.csv"

NO_MAP_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOAD TEAM MAP
# =========================

team_map = {}

if MAP_FILE.exists():
    with open(MAP_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["market"].strip(), row["alias"].strip())
            team_map[key] = row["canonical_team"].strip()

# =========================
# TRACK UNMAPPED
# =========================

unmapped = set()

# =========================
# PROCESS FILES
# =========================

for csv_file in INTAKE_DIR.glob("*.csv"):

    rows = []
    updated = False

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:

            market = row.get("market", "").strip()

            for side in ["home_team", "away_team"]:
                team = row.get(side, "").strip()
                key = (market, team)

                if key in team_map:
                    row[side] = team_map[key]
                    updated = True
                else:
                    unmapped.add((market, team))

            rows.append(row)

    # overwrite file if needed
    if updated:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

# =========================
# WRITE UNMAPPED
# =========================

if unmapped:
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

print("Name normalization complete.")
