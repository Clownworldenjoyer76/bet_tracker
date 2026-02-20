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
RE_TIME = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$", re.IGNORECASE)
RE_PCT  = re.compile(r"(\d+(?:\.\d+)?)%")

# normalize lines (strip ends; drop blanks)
lines = [l.replace("−", "-").strip() for l in raw_text.splitlines() if l.strip()]
n = len(lines)

rows = []
dates_seen = set()
errors = 0

def strip_pcts(s: str) -> str:
    return RE_PCT.sub("", s).strip()

i = 0
while i < n:
    m = RE_DATE.match(lines[i])
    if not m:
        i += 1
        continue

    mm, dd, yyyy = m.groups()
    file_date = f"{yyyy}_{mm}_{dd}"
    dates_seen.add(lines[i])
    i += 1

    if i >= n or not RE_TIME.match(lines[i]):
        log(f"ERROR: Missing/invalid time after date {file_date} (got: {lines[i] if i < n else 'EOF'})")
        errors += 1
        continue

    match_time = lines[i]
    i += 1

    if i + 1 >= n:
        break

    # Teams are the next two lines:
    # In the dump, Team A is listed first (away), Team B second (home).
    team_a_line = lines[i]
    team_b_line = lines[i + 1]
    i += 2

    away_team = strip_pcts(team_a_line)
    home_team = strip_pcts(team_b_line)

    # Collect the NEXT THREE percentages that appear after the teams.
    # DraftKings "Win / Draw / Best" section appears as:
    #   AwayWin%, HomeWin%, Draw%
    pct_vals = []
    j = i
    while j < n and not RE_DATE.match(lines[j]) and len(pct_vals) < 3:
        for v in RE_PCT.findall(lines[j]):
            pct_vals.append(float(v) / 100.0)
            if len(pct_vals) >= 3:
                break
        j += 1

    i = j  # advance

    if len(pct_vals) < 3:
        log(f"ERROR: Could not extract 3 probabilities for {away_team} vs {home_team} | got={pct_vals}")
        errors += 1
        continue

    away_prob = pct_vals[0]
    home_prob = pct_vals[1]
    draw_prob = pct_vals[2]

    total = away_prob + home_prob + draw_prob
    if abs(total - 1.0) > 0.05:
        log(f"ERROR: Prob sum invalid ({total}) for {away_team} vs {home_team} | pcts={pct_vals}")
        errors += 1
        continue

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

if len(dates_seen) != 1:
    log(f"ERROR: Invalid slate (dates_seen={sorted(dates_seen)})")
    raise ValueError("Invalid slate")

if not rows:
    log(f"SUMMARY: upserted 0 rows, {errors} errors")
    raise ValueError("No rows parsed from raw_text")

mm, dd, yyyy = RE_DATE.match(list(dates_seen)[0]).groups()
outfile_date = f"{yyyy}_{mm}_{dd}"

output_dir = Path("docs/win/soccer/00_intake/predictions")
output_dir.mkdir(parents=True, exist_ok=True)
outfile = output_dir / f"soccer_{outfile_date}.csv"

# --- LOAD + SELF-DEDUP EXISTING ---
existing_rows = {}
if outfile.exists():
    with open(outfile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames == FIELDNAMES:
            for r in reader:
                key = (r["match_date"], r["market"], r["home_team"], r["away_team"])
                existing_rows[key] = r
        else:
            log("WARNING: Invalid header detected. Rebuilding clean.")

# --- UPSERT (newest overwrites) ---
for r in rows:
    key = (r["match_date"], r["market"], r["home_team"], r["away_team"])
    existing_rows[key] = r

temp_file = outfile.with_suffix(".tmp")
with open(temp_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for r in existing_rows.values():
        writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

temp_file.replace(outfile)

log(f"SUMMARY: upserted {len(rows)} rows, {errors} errors")
print(f"Wrote {outfile} ({len(rows)} rows processed)")
