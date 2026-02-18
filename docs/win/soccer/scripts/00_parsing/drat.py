#!/usr/bin/env python3

import sys
import re
import csv
from pathlib import Path
from datetime import datetime

ERROR_DIR = Path("docs/win/soccer/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "drat_log.txt"

# Overwrite log at start of each run
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

    if i >= n:
        break

    home_team = lines[i]
    i += 1

    if i >= n:
        break

    away_line = lines[i]
    i += 1

    pct_vals = []

    # Extract any % on away line
    for m in RE_PCT.finditer(away_line):
        pct_vals.append(float(m.group(1)) / 100.0)

    # Remove % tokens from away team line
    away_team = RE_PCT.sub("", away_line).strip()

    # Continue collecting probabilities until we have 3
    while i < n and len(pct_vals) < 3:
        for m in RE_PCT.finditer(lines[i]):
            pct_vals.append(float(m.group(1)) / 100.0)
        i += 1

    if len(pct_vals) != 3:
        log(f"ERROR: Missing probabilities for {home_team} vs {away_team}")
        errors += 1
        continue

    total = sum(pct_vals)
    if abs(total - 1.0) > 0.02:
        log(f"ERROR: Probabilities do not sum to 1 ({total}) for {home_team} vs {away_team}")
        raise ValueError("Probability validation failed")

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

# One-slate protection
if len(dates_seen) > 1:
    log("ERROR: Multiple match_dates detected in intake")
    raise ValueError("Multiple match dates detected — aborting intake")

output_dir = Path("docs/win/soccer/00_intake/predictions")
output_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")
outfile = output_dir / f"{market}_pred_{timestamp}.csv"

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
    writer.writerows(rows)

log(f"SUMMARY: wrote {len(rows)} rows, {errors} errors")
print(f"Wrote {outfile} ({len(rows)} rows)")
