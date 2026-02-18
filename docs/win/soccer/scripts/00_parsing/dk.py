#!/usr/bin/env python3

import sys
import re
import csv
from pathlib import Path
from datetime import datetime

ERROR_DIR = Path("docs/win/soccer/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "dk_log.txt"

# Overwrite log each run
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

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

def clean_team(name):
    return name.replace("-logo", "").strip()

def normalize_odds(o):
    return o.replace("−", "-").strip()

blocks = raw_text.split("More Bets")
rows = []
errors = 0

for block in blocks:
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if "vs" not in lines:
        continue

    try:
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
            if "Today" in l and ("AM" in l or "PM" in l):
                match_time = l
                break

        rows.append([
            league,
            market,
            match_time,
            home_team,
            away_team,
            odds[0],
            odds[1],
            odds[2],
        ])

    except Exception as e:
        log(f"ERROR parsing block: {str(e)}")
        errors += 1

if not rows:
    log("SUMMARY: wrote 0 rows, errors encountered")
    sys.exit()

# Use today's UTC date for sportsbook file grouping
file_date = datetime.utcnow().strftime("%m_%d_%Y")
output_dir = Path("docs/win/soccer/00_intake/sportsbook")
output_dir.mkdir(parents=True, exist_ok=True)

outfile = output_dir / f"soccer_{file_date}.csv"

existing_keys = set()
existing_rows = []

if outfile.exists():
    with open(outfile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["home_team"], row["away_team"])
            existing_keys.add(key)
            existing_rows.append(row)

new_rows = []
for r in rows:
    key = (r[3], r[4])
    if key not in existing_keys:
        new_rows.append(r)
        existing_keys.add(key)

with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "league",
        "market",
        "match_time",
        "home_team",
        "away_team",
        "dk_home_american",
        "dk_draw_american",
        "dk_away_american",
    ])
    writer.writerows(existing_rows)
    writer.writerows(new_rows)

log(f"SUMMARY: wrote {len(new_rows)} new rows, {errors} errors")
print(f"Wrote {outfile} ({len(new_rows)} new rows)")
