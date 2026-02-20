# docs/win/soccer/scripts/00_parsing/drat.py

#!/usr/bin/env python3

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

FIELDNAMES = [
    "league","market","match_date","match_time",
    "home_team","away_team",
    "home_prob","draw_prob","away_prob",
]

RE_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
RE_TIME = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$")
RE_PCT = re.compile(r"(\d+(?:\.\d+)?)%")

lines = [l.replace("−", "-").strip() for l in raw_text.splitlines() if l.strip()]

rows = []
dates_seen = set()

i = 0
n = len(lines)

while i < n:

    date_match = RE_DATE.match(lines[i])
    if not date_match:
        i += 1
        continue

    mm, dd, yyyy = date_match.groups()
    formatted_date = f"{yyyy}_{mm}_{dd}"
    dates_seen.add(lines[i])
    i += 1

    if i >= n or not RE_TIME.match(lines[i]):
        raise ValueError("Missing time after date")

    match_time = lines[i]
    i += 1

    if i + 1 >= n:
        break

    # Team lines may contain percentages — strip them
    away_line = lines[i]
    home_line = lines[i + 1]

    away_team = RE_PCT.sub("", away_line).strip()
    home_team = RE_PCT.sub("", home_line).strip()

    i += 2

    # Collect percentages strictly until we have 3
    pct_vals = []
    start_idx = i

    while i < n and len(pct_vals) < 3:
        # Stop if next match begins
        if RE_DATE.match(lines[i]):
            break

        matches = RE_PCT.findall(lines[i])
        for m in matches:
            pct_vals.append(float(m) / 100.0)

        i += 1

    if len(pct_vals) != 3:
        log(f"ERROR: Could not extract 3 probabilities for {home_team} vs {away_team}")
        raise ValueError("Probability extraction failed")

    total = sum(pct_vals)

    if abs(total - 1.0) > 0.03:
        log(f"ERROR: Probability sum invalid ({total}) for {home_team} vs {away_team}")
        raise ValueError("Probability validation failed")

    # Raw format:
    # pct_vals[0] = Team A (away)
    # pct_vals[1] = Draw
    # pct_vals[2] = Team B (home)

    rows.append({
        "league": league,
        "market": market,
        "match_date": formatted_date,
        "match_time": match_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_prob": f"{pct_vals[2]:.6f}",
        "draw_prob": f"{pct_vals[1]:.6f}",
        "away_prob": f"{pct_vals[0]:.6f}",
    })

if len(dates_seen) != 1:
    raise ValueError("Invalid slate — multiple or zero dates detected")

file_date = formatted_date

output_dir = Path("docs/win/soccer/00_intake/predictions")
output_dir.mkdir(parents=True, exist_ok=True)
outfile = output_dir / f"soccer_{file_date}.csv"

existing_rows = {}

if outfile.exists():
    with open(outfile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames == FIELDNAMES:
            for row in reader:
                key = (
                    row["match_date"],
                    row["market"],
                    row["home_team"],
                    row["away_team"]
                )
                existing_rows[key] = row

for new_row in rows:
    key = (
        new_row["match_date"],
        new_row["market"],
        new_row["home_team"],
        new_row["away_team"]
    )
    existing_rows[key] = new_row

temp_file = outfile.with_suffix(".tmp")

with open(temp_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for r in existing_rows.values():
        writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

temp_file.replace(outfile)

print(f"Wrote {outfile} ({len(rows)} rows processed)")
