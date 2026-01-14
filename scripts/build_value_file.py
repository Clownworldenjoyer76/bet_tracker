#!/usr/bin/env python3
"""
Build Value Bets File from Edge Files (NCAAB)

Reads:
  docs/win/edge/edge_ncaab_*.csv

Writes:
  docs/win/value/value_ncaab_YYYY_MM_DD.csv

Adds:
  units_to_bet

Rules:
- Baseline = 1.0 unit ($0.10)
- Stake tiers based strictly on win_probability and acceptable_american_odds
- Output ONLY bets with units_to_bet > 0.10
- No odds recalculation
- No external data
"""

import csv
import glob
from pathlib import Path
from datetime import datetime

EDGE_DIR = Path("docs/win/edge")
VALUE_DIR = Path("docs/win/value")
VALUE_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE = "ncaab"

def determine_units(win_prob: float, acceptable_american: int) -> float:
    if win_prob >= 0.75 and acceptable_american >= -300:
        return 1.50
    if win_prob >= 0.70 and acceptable_american >= -250:
        return 1.25
    if win_prob >= 0.60:
        return 1.00
    return 0.00

def main():
    edge_files = sorted(glob.glob(str(EDGE_DIR / f"edge_{LEAGUE}_*.csv")))
    if not edge_files:
        raise FileNotFoundError("No edge_ncaab files found")

    latest_file = edge_files[-1]

    today = datetime.utcnow()
    out_path = VALUE_DIR / f"value_{LEAGUE}_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    with open(latest_file, newline="", encoding="utf-8") as infile, \
         open(out_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["units_to_bet"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            try:
                win_prob = float(row["win_probability"])
                acceptable_american = int(row["acceptable_american_odds"])
            except Exception:
                continue

            units = determine_units(win_prob, acceptable_american)

            # FILTER: only include bets with units_to_bet > 0.10
            if units <= 0.10:
                continue

            row["units_to_bet"] = f"{units:.2f}"
            writer.writerow(row)

if __name__ == "__main__":
    main()
