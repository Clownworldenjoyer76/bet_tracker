#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/drat.py

import sys
import re
import csv
from pathlib import Path
from datetime import datetime

ERROR_DIR = Path("docs/win/soccer/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "drat_log.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

if len(sys.argv) < 4:
    raise ValueError("Usage: drat.py <league> <market> <raw_text>")

league = "soccer"
market_input = sys.argv[2].strip()
raw_text = sys.argv[3]

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

FIELDNAMES = [
    "league","market","match_date","match_time",
    "home_team","away_team",
    "home_prob","draw_prob","away_prob",
]

RE_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
RE_TIME = re.compile(r"\d{1,2}:\d{2}\s*(AM|PM)", re.IGNORECASE)
RE_PCT  = re.compile(r"(\d+(?:\.\d+)?)%")

lines = [l.replace("−", "-").strip() for l in raw_text.splitlines() if l.strip()]
n = len(lines)

rows = []
dates_seen = set()

i = 0
while i < n:
    m = RE_DATE.search(lines[i])
    if not m:
        i += 1
        continue

    mm, dd, yyyy = m.groups()
    file_date = f"{yyyy}_{mm}_{dd}"
    dates_seen.add(file_date)
    i += 1

    if i >= n or not RE_TIME.search(lines[i]):
        i += 1
        continue

    match_time = lines[i]
    i += 1

    if i + 1 >= n:
        break

    # Team A then Team B
    away_team = RE_PCT.sub("", lines[i]).strip()
    home_team = RE_PCT.sub("", lines[i + 1]).strip()
    i += 2

    # Collect next 3 percentages ONLY
    pct_vals = []
    while i < n and len(pct_vals) < 3:
        found = RE_PCT.findall(lines[i])
        for v in found:
            pct_vals.append(float(v) / 100.0)
            if len(pct_vals) == 3:
                break
        i += 1

    if len(pct_vals) != 3:
        continue

    # Dump order: Team A %, Team B %, Draw %
    away_prob = pct_vals[0]
    home_prob = pct_vals[1]
    draw_prob = pct_vals[2]

    rows.append({
        "league": league,
        "market": market,
        "match_date": file_date,
        "match_time": match_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_prob": f"{home_prob:.6f}",
        "draw_prob": f"{draw_prob:.6f}",
        "away_prob": f"{away_prob:.6f}",
    })

if not rows:
    raise ValueError("No rows parsed from raw_text")

outfile = Path("docs/win/soccer/00_intake/predictions") / f"soccer_{file_date}.csv"
outfile.parent.mkdir(parents=True, exist_ok=True)

with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {outfile} ({len(rows)} rows)")
