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

# overwrite log each run
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


# =========================
# MARKET NORMALIZATION
# =========================

MARKET_MAP = {
    "la liga": "laliga",
    "laliga": "laliga",
    "epl": "epl",
    "serie a": "seriea",
    "seriea": "seriea",
    "bundesliga": "bundesliga",
    "ligue 1": "ligue1",
    "ligue1": "ligue1",
}

def normalize_market(value: str) -> str:
    if not value:
        return ""
    v = value.strip().lower()
    return MARKET_MAP.get(v, v)


# =========================
# LEAGUE NORMALIZATION
# =========================

def normalize_league(value: str) -> str:
    if not value:
        return value
    v = value.strip().lower()
    if v == "soccer":
        return "Soccer"
    return value


# =========================
# LOAD TEAM MAP
# =========================

team_map = {}

if MAP_FILE.exists():
    with open(MAP_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            market = normalize_market(row.get("market"))
            alias = (row.get("alias") or "").strip().lower()
            canonical = (row.get("canonical_team") or "").strip()

            if market and alias and canonical:
                team_map[(market, alias)] = canonical
else:
    log("WARNING: team_map_soccer.csv not found")


# =========================
# BUILD FILE LIST
# =========================

market_files = []
combined_files = []

for f in INTAKE_DIR.rglob("*.csv"):
    if "combined" in f.parts:
        combined_files.append(f)
    else:
        market_files.append(f)

files_to_process = sorted(market_files) + sorted(combined_files)


# =========================
# PROCESS FILES
# =========================

unmapped = set()

files_processed = 0
rows_processed = 0
rows_updated = 0

for csv_file in files_to_process:

    files_processed += 1
    updated_rows = []
    modified = False

    with open(csv_file, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        if "home_team" not in fieldnames or "away_team" not in fieldnames:
            continue

        for row in reader:

            rows_processed += 1

            # =========================
            # MARKET NORMALIZATION FIX
            # =========================
            if "market" in row:
                original_market = row.get("market")
                new_market = normalize_market(original_market)
                if original_market != new_market:
                    row["market"] = new_market
                    modified = True

            # =========================
            # LEAGUE NORMALIZATION FIX
            # =========================
            if "league" in row:
                original_league = row.get("league")
                new_league = normalize_league(original_league)
                if original_league != new_league:
                    row["league"] = new_league
                    modified = True

            market = row.get("market", "")

            for side in ["home_team", "away_team"]:

                team_raw = (row.get(side) or "").strip()
                team_norm = team_raw.lower().strip()

                if not team_raw:
                    continue

                key = (market, team_norm)

                if key in team_map:

                    canonical = team_map[key]

                    if row[side] != canonical:
                        row[side] = canonical
                        modified = True
                        rows_updated += 1

                else:
                    unmapped.add((market, team_raw))

            updated_rows.append(row)

    if modified and fieldnames:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)


# =========================
# WRITE UNMAPPED
# =========================

with open(NO_MAP_FILE, "w", newline="", encoding="utf-8") as f:

    writer = csv.writer(f)
    writer.writerow(["market", "team"])

    for market, team in sorted(unmapped):
        writer.writerow([market, team])


# =========================
# LOG SUMMARY
# =========================

log(
    f"SUMMARY: files_processed={files_processed}, "
    f"rows_processed={rows_processed}, "
    f"rows_updated={rows_updated}, "
    f"unmapped_found={len(unmapped)}"
)

print("Name normalization complete.")
