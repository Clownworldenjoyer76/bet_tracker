#!/usr/bin/env python3

import sys
import re
import csv
from pathlib import Path
from datetime import datetime

ERROR_DIR = Path("docs/win/soccer/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "drat_log.txt"

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

RE_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
RE_TIME = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$")
RE_PCT = re.compile(r"(\d+(?:\.\d+)?)%")

rows = []
dates_seen = set()
errors = 0

lines = [l.replace("−", "-").strip() for l in raw_text.splitlines() if l.strip()]
i = 0
n = len(lines)

while i < n:
    if not RE_DATE.match(lines[i]):
        i += 1
        continue

    match_date = lines[i]
    dates_seen.add(match_date)
    i += 1

    if i >= n or not RE_TIME.match(lines[i]):
        log("ERROR: Missing time after date")
        errors += 1
        continue

    match_time = lines[i]
    i += 1

    if i + 1 >= n:
        break

    away_team = lines[i]
    home_line = lines[i + 1]
    i += 2

    pct_vals = []
    for m in RE_PCT.finditer(home_line):
        pct_vals.append(float(m.group(1)) / 100.0)

    home_team = RE_PCT.sub("", home_line).strip()

    while i < n and len(pct_vals) < 3:
        for m in RE_PCT.finditer(lines[i]):
            pct_vals.append(float(m.group(1)) / 100.0)
        i += 1

    if len(pct_vals) != 3:
        log(f"ERROR: Missing probabilities for {home_team} vs {away_team}")
        errors += 1
        continue

    rows.append([
        league,
        market,
        match_date,
        match_time,
        home_team,
        away_team,
        f"{pct_vals[0]:.6f}",
        f"{pct_vals[1]:.6f}",
        f"{pct_vals[2]:.6f}",
    ])

if len(dates_seen) != 1:
    log("ERROR: Multiple or zero match_dates detected")
    raise ValueError("Invalid slate")

file_date = list(dates_seen)[0].replace("/", "_")
output_dir = Path("docs/win/soccer/00_intake/predictions")
output_dir.mkdir(parents=True, exist_ok=True)

outfile = output_dir / f"soccer_{file_date}.csv"

existing_keys = set()
existing_rows = []

if outfile.exists():
    with open(outfile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["match_date"], row["home_team"], row["away_team"])
            existing_keys.add(key)
            existing_rows.append(row)

new_rows = []
for r in rows:
    key = (r[2], r[4], r[5])
    if key not in existing_keys:
        new_rows.append(r)
        existing_keys.add(key)

with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "league",
        "market",
        "match_date",
        "match_time",
        "home_team",
        "away_team",
        "home_prob",
        "draw_prob",
        "away_prob",
    ])
    writer.writerows(existing_rows)
    writer.writerows(new_rows)

log(f"SUMMARY: wrote {len(new_rows)} new rows, {errors} errors")
print(f"Wrote {outfile} ({len(new_rows)} new rows)")
