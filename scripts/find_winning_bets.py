#!/usr/bin/env python3

"""
find_winning_bets.py

Reads:
- DraftKings daily odds file:
    docs/win/DK_{year}_{month}_{day}.xlsx

- Edge files:
    docs/win/edge/edge_{league}_{year}_{month}_{day}.csv

- Team mapping:
    mappings/team_map.csv

Outputs:
- docs/win/final/winning_bets_{year}_{month}_{day}.csv

Design goals:
- Zero assumptions
- League-specific logic isolated in one place
- Safe handling for leagues with no DK data (e.g. soc)
"""

import sys
import csv
from pathlib import Path
from datetime import date
import pandas as pd

ROOT = Path(".")
EDGE_DIR = ROOT / "docs" / "win" / "edge"
DK_DIR = ROOT / "docs" / "win"
MAP_PATH = ROOT / "mappings" / "team_map.csv"
OUT_DIR = ROOT / "docs" / "win" / "final"

OUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# League-specific logic hooks
# -----------------------------
def evaluate_edge(row, dk_row, league):
    """
    Return True if this is a bet we want to take.
    THIS IS WHERE YOU WILL CHANGE LOGIC PER LEAGUE.
    """

    if league == "nba":
        return row["edge"] > 0

    if league == "nhl":
        return row["edge"] > 0

    if league == "nfl":
        return row["edge"] > 0

    if league == "soc":
        # No DK data exists
        return False

    return False


# -----------------------------
# Main
# -----------------------------
def main():
    today = date.today()
    y, m, d = today.year, f"{today.month:02}", f"{today.day:02}"

    dk_path = DK_DIR / f"DK_{y}_{m}_{d}.xlsx"

    if not dk_path.exists():
        print(f"DK file not found: {dk_path}")
        sys.exit(1)

    dk_df = pd.read_excel(dk_path)

    team_map = {}
    with MAP_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team_map[(row["league"], row["dk_team"])] = row["edge_team"]

    output_rows = []

    for edge_file in EDGE_DIR.glob(f"edge_*_{y}_{m}_{d}.csv"):
        league = edge_file.stem.split("_")[1]

        edge_df = pd.read_csv(edge_file)

        if league == "soc":
            continue

        for _, edge_row in edge_df.iterrows():
            mapped_team = team_map.get((league, edge_row["team"]))
            if not mapped_team:
                continue

            dk_match = dk_df[
                (dk_df["league"] == league) &
                (dk_df["team"] == mapped_team)
            ]

            if dk_match.empty:
                continue

            dk_row = dk_match.iloc[0]

            if evaluate_edge(edge_row, dk_row, league):
                output_rows.append({
                    "date": f"{y}-{m}-{d}",
                    "league": league,
                    "team": edge_row["team"],
                    "opponent": edge_row["opponent"],
                    "edge": edge_row["edge"],
                    "dk_odds": dk_row["moneyline"],
                    "handle_pct": dk_row.get("handle_pct"),
                    "bet_pct": dk_row.get("bet_pct"),
                })

    out_path = OUT_DIR / f"winning_bets_{y}_{m}_{d}.csv"
    pd.DataFrame(output_rows).to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
