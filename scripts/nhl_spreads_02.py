#!/usr/bin/env python3
"""
scripts/nhl_spreads_02.py

Purpose:
- Populate existing nhl_spreads_*.csv files with values derived from final_nhl_*.csv

Matching rules (ALL must match):
- game_id
- final_nhl.team == nhl_spreads.away_team
- final_nhl.opponent == nhl_spreads.home_team

Writes values ONLY to the specified columns.
"""

import csv
from pathlib import Path
import sys
import re

SPREADS_DIR = Path("docs/win/nhl/spreads")
FINAL_DIR = Path("docs/win/final")

REQUIRED_SPREAD_COLUMNS = [
    "game_id",
    "away_team",
    "home_team",
]

REQUIRED_FINAL_COLUMNS = [
    "game_id",
    "team",
    "opponent",
    "win_probability",
    "personally_acceptable_american_odds",
    "personally_acceptable_decimal_odds",
]

def extract_date(filename: str) -> str:
    match = re.search(r"(\d{4}_\d{2}_\d{2})", filename)
    if not match:
        raise ValueError(f"Could not extract date from filename: {filename}")
    return match.group(1)

def load_final_rows(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        missing = [c for c in REQUIRED_FINAL_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path.name} missing required columns: {missing}")

        for row in reader:
            rows.append(row)

    return rows

def process_spread_file(spread_path: Path):
    date_str = extract_date(spread_path.name)
    final_path = FINAL_DIR / f"final_nhl_{date_str}.csv"

    if not final_path.exists():
        print(f"Missing final file for {spread_path.name}", file=sys.stderr)
        return

    final_rows = load_final_rows(final_path)

    with spread_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        spread_rows = list(reader)
        headers = reader.fieldnames

    missing = [c for c in REQUIRED_SPREAD_COLUMNS if c not in headers]
    if missing:
        raise ValueError(f"{spread_path.name} missing required columns: {missing}")

    for srow in spread_rows:
        matches = [
            frow for frow in final_rows
            if frow["game_id"] == srow["game_id"]
            and frow["team"] == srow["away_team"]
            and frow["opponent"] == srow["home_team"]
        ]

        if len(matches) != 2:
            continue

        away = matches[0]
        home = matches[1]

        srow["away_win_prob"] = away["win_probability"]
        srow["home_win_prob"] = home["win_probability"]

        srow["away_amer_odds"] = away["personally_acceptable_american_odds"]
        srow["home_amer_odds"] = home["personally_acceptable_american_odds"]

        srow["away_deci_odds"] = away["personally_acceptable_decimal_odds"]
        srow["home_deci_odds"] = home["personally_acceptable_decimal_odds"]

        if float(away["win_probability"]) < float(home["win_probability"]):
            srow["underdog"] = srow["away_team"]
        else:
            srow["underdog"] = srow["home_team"]

        srow["puck_line"] = "+1.5"
        srow["puck_line_fair_deci"] = ""
        srow["puck_line_fair_amer"] = ""
        srow["puck_line_acceptable_deci"] = ""
        srow["puck_line_acceptable_amer"] = ""
        srow["puck_line_juiced_deci"] = ""
        srow["puck_line_juiced_amer"] = ""
        srow["league"] = "nhl_spread"

    with spread_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(spread_rows)

    print(f"Updated: {spread_path}")

def main():
    files = sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))

    if not files:
        print("No nhl_spreads files found.", file=sys.stderr)
        sys.exit(1)

    for f in files:
        process_spread_file(f)

if __name__ == "__main__":
    main()
