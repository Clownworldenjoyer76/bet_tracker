#!/usr/bin/env python3
"""
scripts/nhl_spreads_02.py

Purpose:
- Read existing nhl_spreads_*.csv files under docs/win/nhl/spreads/
- Match rows against final_nhl_*.csv on:
    * game_id
    * final.team      == spreads.away_team
    * final.opponent  == spreads.home_team
- Copy / rename values from final_nhl_*.csv into nhl_spreads_*.csv
- Add required new columns and values
- Write back to the SAME nhl_spreads_*.csv file (augmenting it)

This script does NOT infer, optimize, or alter unrelated data.
"""

import csv
from pathlib import Path
from typing import Dict, List

ROOT = Path(".")
FINAL_DIR = ROOT / "docs" / "win" / "nhl"
SPREADS_DIR = ROOT / "docs" / "win" / "nhl" / "spreads"


def load_final_files() -> Dict[str, List[dict]]:
    """
    Load all final_nhl_*.csv files and index by game_id.
    Each game_id maps to a list of rows (one per team).
    """
    final_index: Dict[str, List[dict]] = {}

    for path in FINAL_DIR.glob("final_nhl_*.csv"):
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game_id = row.get("game_id")
                if not game_id:
                    continue
                final_index.setdefault(game_id, []).append(row)

    return final_index


def find_team_row(rows: List[dict], team: str, opponent: str) -> dict:
    """
    From final rows for a game_id, find the row where:
    team == team AND opponent == opponent
    """
    for r in rows:
        if r.get("team") == team and r.get("opponent") == opponent:
            return r
    return {}


def process_spreads_file(path: Path, final_index: Dict[str, List[dict]]) -> None:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    # Required new columns
    new_columns = [
        "away_win_prob",
        "home_win_prob",
        "away_amer_odds",
        "home_amer_odds",
        "away_deci_odds",
        "home_deci_odds",
        "underdog",
        "puck_line",
        "puck_line_fair_deci",
        "puck_line_fair_amer",
        "puck_line_acceptable_deci",
        "puck_line_acceptable_amer",
        "puck_line_juiced_deci",
        "puck_line_juiced_amer",
        "league",
    ]

    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)

    for row in rows:
        game_id = row.get("game_id")
        away_team = row.get("away_team")
        home_team = row.get("home_team")

        if not game_id or game_id not in final_index:
            continue

        final_rows = final_index[game_id]

        away_final = find_team_row(final_rows, away_team, home_team)
        home_final = find_team_row(final_rows, home_team, away_team)

        if not away_final or not home_final:
            continue

        # Copy values
        row["away_win_prob"] = away_final.get("win_probability", "")
        row["home_win_prob"] = home_final.get("win_probability", "")

        row["away_amer_odds"] = away_final.get("personally_acceptable_american_odds", "")
        row["home_amer_odds"] = home_final.get("personally_acceptable_american_odds", "")

        row["away_deci_odds"] = away_final.get("personally_acceptable_decimal_odds", "")
        row["home_deci_odds"] = home_final.get("personally_acceptable_decimal_odds", "")

        # Underdog determination
        try:
            away_wp = float(row["away_win_prob"])
            home_wp = float(row["home_win_prob"])
            if away_wp < home_wp:
                row["underdog"] = away_team
            elif home_wp < away_wp:
                row["underdog"] = home_team
            else:
                row["underdog"] = ""
        except Exception:
            row["underdog"] = ""

        # Static / blank fields
        row["puck_line"] = "+1.5"
        row["puck_line_fair_deci"] = ""
        row["puck_line_fair_amer"] = ""
        row["puck_line_acceptable_deci"] = ""
        row["puck_line_acceptable_amer"] = ""
        row["puck_line_juiced_deci"] = ""
        row["puck_line_juiced_amer"] = ""
        row["league"] = "nhl_spread"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    final_index = load_final_files()

    for spreads_file in SPREADS_DIR.glob("nhl_spreads_*.csv"):
        process_spreads_file(spreads_file, final_index)


if __name__ == "__main__":
    main()
