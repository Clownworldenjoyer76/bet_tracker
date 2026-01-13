#!/usr/bin/env python3

"""
find_winning_bets.py
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
def evaluate_edge(edge_american, row, dk_row, league):
    if league == "nba":
        return edge_american >= 0
    if league == "nhl":
        return edge_american >= 0
    if league == "nfl":
        return edge_american >= 0
    if league == "soc":
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

    # -----------------------------
    # Load team mapping
    # -----------------------------
    team_map = {}
    with MAP_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team_map[(row["league"], row["dk_team"])] = row["canonical_team"]

    # -----------------------------
    # Prepare output schema (ALWAYS written)
    # -----------------------------
    output_columns = [
        "date",
        "league",
        "team",
        "opponent",
        "edge_american",
        "dk_odds",
        "handle_pct",
        "bet_pct",
    ]

    output_rows = []

    # -----------------------------
    # Process edge files
    # -----------------------------
    for edge_file in EDGE_DIR.glob(f"edge_*_{y}_{m}_{d}.csv"):
        league = edge_file.stem.split("_")[1]
        edge_df = pd.read_csv(edge_file)

        if league == "soc":
            continue

        for _, edge_row in edge_df.iterrows():
            canonical_team = edge_row["team"]

            dk_team_matches = [
                dk_team
                for (lg, dk_team), canon in team_map.items()
                if lg == league and canon == canonical_team
            ]

            if not dk_team_matches:
                print(
                    f"ERROR: No team mapping found for "
                    f"league='{league}', canonical_team='{canonical_team}'"
                )
                sys.exit(1)

            dk_team = dk_team_matches[0]

            dk_match = dk_df[
                (dk_df["league"] == league) &
                (dk_df["team"] == dk_team)
            ]

            if dk_match.empty:
                print(
                    f"ERROR: DK odds not found for "
                    f"league='{league}', dk_team='{dk_team}'"
                )
                sys.exit(1)

            dk_row = dk_match.iloc[0]

            # -----------------------------
            # Compute edge directly
            # -----------------------------
            edge_american = (
                edge_row["acceptable_american_odds"]
                - edge_row["fair_american_odds"]
            )

            if evaluate_edge(edge_american, edge_row, dk_row, league):
                output_rows.append({
                    "date": f"{y}-{m}-{d}",
                    "league": league,
                    "team": canonical_team,
                    "opponent": edge_row["opponent"],
                    "edge_american": edge_american,
                    "dk_odds": dk_row["moneyline"],
                    "handle_pct": dk_row.get("handle_pct"),
                    "bet_pct": dk_row.get("bet_pct"),
                })

    out_path = OUT_DIR / f"winning_bets_{y}_{m}_{d}.csv"
    pd.DataFrame(output_rows, columns=output_columns).to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
