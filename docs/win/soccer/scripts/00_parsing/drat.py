#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/drat.py

import sys
import re
import csv
from pathlib import Path
from datetime import datetime

# =========================
# ARGUMENTS
# =========================

league_input = sys.argv[1].strip()
market_input = sys.argv[2].strip()
raw_text = sys.argv[3]

# =========================
# NORMALIZE LEAGUE / MARKET
# =========================

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
# REGEX
# =========================

RE_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
RE_TIME = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$", re.IGNORECASE)
RE_PCT = re.compile(r"(\d+(?:\.\d+)?)%")

# =========================
# HELPERS
# =========================

def clean_line(s: str) -> str:
    return s.replace("\u2212", "-").strip()

def is_header_noise(s: str) -> bool:
    if not s:
        return True
    low = s.lower()
    return (
        low.startswith("time\tteams") or
        low.startswith("time teams") or
        low in {"time", "teams", "win", "draw", "best", "ml", "goals", "total", "o/u", "bet", "value", "more details"} or
        "more details" in low
    )

def pct_to_prob(p: str) -> str:
    try:
        v = float(p) / 100.0
        if v < 0:
            v = 0.0
        if v > 1:
            v = 1.0
        return f"{v:.6f}"
    except Exception:
        return ""

# =========================
# PREP LINES
# =========================

raw_lines = []
for ln in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
    ln = clean_line(ln)
    if not ln:
        continue
    if is_header_noise(ln):
        continue
    raw_lines.append(ln)

# =========================
# PARSE
# =========================

rows = []
i = 0
n = len(raw_lines)

while i < n:
    line = raw_lines[i]

    # Locate date
    if not RE_DATE.match(line):
        i += 1
        continue

    match_date = line
    i += 1
    if i >= n:
        break

    # Locate time
    match_time = raw_lines[i]
    if not RE_TIME.match(match_time):
        recovered_time = ""
        for j in range(i, min(i + 4, n)):
            if RE_TIME.match(raw_lines[j]):
                recovered_time = raw_lines[j]
                i = j + 1
                break
        if not recovered_time:
            i += 1
            continue
        match_time = recovered_time
    else:
        i += 1

    if i + 1 >= n:
        break

    home_team = raw_lines[i]
    away_team = raw_lines[i + 1]
    i += 2

    # Collect window until next date
    window = []
    j = i
    while j < n and not RE_DATE.match(raw_lines[j]) and len(window) < 40:
        window.append(raw_lines[j])
        j += 1

    # Extract first 3 percentages
    pct_vals = []
    for w in window:
        for m in RE_PCT.finditer(w):
            pct_vals.append(m.group(1))
            if len(pct_vals) >= 3:
                break
        if len(pct_vals) >= 3:
            break

    home_prob = pct_to_prob(pct_vals[0]) if len(pct_vals) >= 1 else ""
    draw_prob = pct_to_prob(pct_vals[1]) if len(pct_vals) >= 2 else ""
    away_prob = pct_to_prob(pct_vals[2]) if len(pct_vals) >= 3 else ""

    rows.append([
        league,
        market,
        match_date,
        match_time,
        home_team,
        away_team,
        home_prob,
        draw_prob,
        away_prob,
    ])

    i = j

# =========================
# OUTPUT
# =========================

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

print(f"Wrote {outfile} ({len(rows)} rows)")
