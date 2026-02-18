#!/usr/bin/env python3

import sys
from pathlib import Path
from datetime import datetime

# =========================
# ARGUMENTS
# =========================

league_input = sys.argv[1].strip()
market_input = sys.argv[2].strip()
raw_text = sys.argv[3]

# =========================
# NORMALIZE HEADERS
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
# OUTPUT PATH
# =========================

base_dir = Path("docs/win/soccer/00_intake/sportsbook")
base_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")
outfile = base_dir / f"{market}_dk_raw_{timestamp}.txt"

# =========================
# WRITE RAW TEXT
# =========================

with open(outfile, "w", encoding="utf-8") as f:
    f.write(f"league={league}\n")
    f.write(f"market={market}\n")
    f.write("source=draftkings\n")
    f.write("----RAW----\n")
    f.write(raw_text)

print(f"Wrote {outfile}")
