#!/usr/bin/env python3

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
# HELPERS
# =========================

def clean_team(name):
    return name.replace("-logo", "").strip()

def normalize_odds(o):
    o = o.replace("−", "-").replace("+", "+").strip()
    return o

# =========================
# SPLIT MATCHES
# =========================

blocks = raw_text.split("More Bets")
rows = []

for block in blocks:
    lines = [l.strip() for l in block.splitlines() if l.strip()]

    if "vs" not in lines:
        continue

    try:
        vs_index = lines.index("vs")

        home_team = clean_team(lines[vs_index - 1])
        away_team = clean_team(lines[vs_index + 2])

        # Odds are first 3 +/− numbers found
        odds = [normalize_odds(x) for x in lines if re.match(r"[+\-−]\d+", x)]
        if len(odds) < 3:
            continue

        dk_home = odds[0]
        dk_draw = odds[1]
        dk_away = odds[2]

        # Time line contains "Today" and "PM/AM"
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
            dk_home,
            dk_draw,
            dk_away
        ])

    except Exception:
        continue

# =========================
# OUTPUT
# =========================

output_dir = Path("docs/win/soccer/00_intake/sportsbook")
output_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")
outfile = output_dir / f"{market}_dk_{timestamp}.csv"

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
        "dk_away_american"
    ])
    writer.writerows(rows)

print(f"Wrote {outfile} ({len(rows)} rows)")
