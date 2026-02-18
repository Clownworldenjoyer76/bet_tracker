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

FIELDNAMES = [
    "league",
    "market",
    "match_date",
    "match_time",
    "home_team",
    "away_team",
    "home_prob",
    "draw_prob",
    "away_prob",
]

RE_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
RE_TIME = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$")
RE_PCT = re.compile(r"(\d+(?:\.\d+)?)%")

rows = []
dates_seen = set()
errors = 0

lines = [l.replace("−", "-").strip() for l in raw_text.splitlines() if l.strip()]
i = 0
n = len(lines)

while i < n:
    date_match = RE_DATE.match(lines[i])
    if not date_match:
        i += 1
        continue

    mm, dd, yyyy = date_match.groups()
    original_date = lines[i]
    formatted_date = f"{yyyy}_{mm}_{dd}"

    dates_seen.add(original_date)
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

    total = sum(pct_vals)
    if abs(total - 1.0) > 0.02:
        log(f"ERROR: Probabilities do not sum to 1 ({total}) for {home_team} vs {away_team}")
        raise ValueError("Probability validation failed")

    rows.append({
        "league": league,
        "market": market,
        "match_date": formatted_date,
        "match_time": match_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_prob": f"{pct_vals[0]:.6f}",
        "draw_prob": f"{pct_vals[1]:.6f}",
        "away_prob": f"{pct_vals[2]:.6f}",
    })

if len(dates_seen) != 1:
    log("ERROR: Multiple or zero match_dates detected")
    raise ValueError("Invalid slate")

mm, dd, yyyy = RE_DATE.match(list(dates_seen)[0]).groups()
file_date = f"{mm}_{dd}_{yyyy}"

output_dir = Path("docs/win/soccer/00_intake/predictions")
output_dir.mkdir(parents=True, exist_ok=True)
outfile = output_dir / f"soccer_{file_date}.csv"

existing_rows = []

if outfile.exists():
    with open(outfile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames != FIELDNAMES:
            log("WARNING: Invalid header detected. Rebuilding clean.")
        else:
            for row in reader:
                if all(k in row for k in FIELDNAMES):
                    existing_rows.append(row)

for new_row in rows:
    key = (
        new_row["match_date"],
        new_row["market"],
        new_row["home_team"],
        new_row["away_team"],
    )

    existing_rows = [
        r for r in existing_rows
        if (
            r["match_date"],
            r["market"],
            r["home_team"],
            r["away_team"],
        ) != key
    ]

    existing_rows.append(new_row)

temp_file = outfile.with_suffix(".tmp")

with open(temp_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for r in existing_rows:
        writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

temp_file.replace(outfile)

log(f"SUMMARY: upserted {len(rows)} rows, {errors} errors")
print(f"Wrote {outfile} ({len(rows)} rows processed)")
