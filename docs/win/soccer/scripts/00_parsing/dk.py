#!/usr/bin/env python3

import sys
import re
import csv
from pathlib import Path
from datetime import datetime

# =========================
# PATHS
# =========================

ERROR_DIR = Path("docs/win/soccer/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "dk_log.txt"

# Overwrite log each run
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# ARGUMENTS
# =========================

league_input = sys.argv[1].strip()
market_input = sys.argv[2].strip()
raw_text = sys.argv[3]

league = "soccer"

market_map = {
    "MLS": "mls",
    "EPL": "epl",
    "Ligue 1": "ligue1",
    "Serie A": "seriea",
    "La Liga": "laliga",
    "Bundesliga": "bundesliga",
}

market = market_map.get(market_input)
if not market:
    raise ValueError("Invalid soccer market")

# =========================
# CONSTANTS
# =========================

FIELDNAMES = [
    "league",
    "market",
    "match_date",
    "match_time",
    "home_team",
    "away_team",
    "dk_home_american",
    "dk_draw_american",
    "dk_away_american",
]

RE_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")

# =========================
# HELPERS
# =========================

def clean_team(name):
    return name.replace("-logo", "").strip()

def normalize_odds(o):
    return o.replace("−", "-").strip()

# =========================
# PARSE
# =========================

blocks = raw_text.split("More Bets")
rows = []
errors = 0
match_date = None

for block in blocks:
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if "vs" not in lines:
        continue

    try:
        # Extract match_date from block if present
        for l in lines:
            if RE_DATE.match(l):
                match_date = l
                break

        vs_index = lines.index("vs")
        home_team = clean_team(lines[vs_index - 1])
        away_team = clean_team(lines[vs_index + 2])

        odds = [normalize_odds(x) for x in lines if re.match(r"[+\-−]\d+", x)]
        if len(odds) != 3:
            log(f"ERROR: Expected 3 odds but found {len(odds)} for {home_team} vs {away_team}")
            errors += 1
            continue

        match_time = ""
        for l in lines:
            if "Today" in l or ("AM" in l or "PM" in l):
                match_time = l
                break

        rows.append({
            "league": league,
            "market": market,
            "match_date": match_date if match_date else "",
            "match_time": match_time,
            "home_team": home_team,
            "away_team": away_team,
            "dk_home_american": odds[0],
            "dk_draw_american": odds[1],
            "dk_away_american": odds[2],
        })

    except Exception as e:
        log(f"ERROR parsing block: {str(e)}")
        errors += 1

if not rows:
    log("SUMMARY: wrote 0 rows, errors encountered")
    sys.exit()

if not match_date:
    raise ValueError("Match date not found in DK input")

file_date = match_date.replace("/", "_")

output_dir = Path("docs/win/soccer/00_intake/sportsbook")
output_dir.mkdir(parents=True, exist_ok=True)
outfile = output_dir / f"soccer_{file_date}.csv"

# =========================
# LOAD EXISTING (STRICT VALIDATION)
# =========================

existing_rows = []
existing_keys = set()

if outfile.exists():
    with open(outfile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames != FIELDNAMES:
            log("WARNING: Invalid header detected. Rebuilding file clean.")
        else:
            for row in reader:
                if not all(k in row for k in FIELDNAMES):
                    continue

                key = (
                    row["match_date"],
                    row["market"],
                    row["home_team"],
                    row["away_team"],
                )

                existing_keys.add(key)
                existing_rows.append(row)

# =========================
# UPSERT LOGIC
# =========================

for row in rows:
    key = (
        row["match_date"],
        row["market"],
        row["home_team"],
        row["away_team"],
    )

    # Remove existing if present (upsert)
    existing_rows = [
        r for r in existing_rows
        if (
            r["match_date"],
            r["market"],
            r["home_team"],
            r["away_team"],
        ) != key
    ]

    existing_rows.append(row)
    existing_keys.add(key)

# =========================
# ATOMIC WRITE
# =========================

temp_file = outfile.with_suffix(".tmp")

with open(temp_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for r in existing_rows:
        writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

temp_file.replace(outfile)

log(f"SUMMARY: upserted {len(rows)} rows, {errors} errors")
print(f"Wrote {outfile} ({len(rows)} rows processed)")
