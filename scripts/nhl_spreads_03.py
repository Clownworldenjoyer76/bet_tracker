#!/usr/bin/env python3
"""
scripts/nhl_spreads_03.py

Purpose:
- Insert two new columns into docs/win/nhl/spreads/nhl_spreads_*.csv:
    home_goals
    away_goals

Source of truth:
- docs/win/final/final_nhl_*.csv

Rules:
- Match on game_id
- final_nhl.team == spreads.away_team  -> away_goals
- final_nhl.team == spreads.home_team  -> home_goals
- Each final_nhl file has ONE row per team with a "goals" value
- Each spreads file has ONE row per game

Nothing else is modified.
"""

import csv
from pathlib import Path
from typing import Dict, List

ROOT = Path(".")
FINAL_DIR = ROOT / "docs" / "win" / "final"
SPREADS_DIR = ROOT / "docs" / "win" / "nhl" / "spreads"


def load_final_goals() -> Dict[str, Dict[str, str]]:
    """
    Returns:
        {
          game_id: {
            team_name: goals
          }
        }
    """
    data: Dict[str, Dict[str, str]] = {}

    for path in FINAL_DIR.glob("final_nhl_*.csv"):
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game_id = row.get("game_id")
                team = row.get("team")
                goals = row.get("goals")

                if not game_id or not team:
                    continue

                data.setdefault(game_id, {})[team] = goals

    return data


def process_spreads_file(path: Path, final_goals: Dict[str, Dict[str, str]]) -> None:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    # Ensure required columns exist
    if "home_goals" not in fieldnames:
        fieldnames.append("home_goals")
    if "away_goals" not in fieldnames:
        fieldnames.append("away_goals")

    for row in rows:
        game_id = row.get("game_id")
        home_team = row.get("home_team")
        away_team = row.get("away_team")

        if not game_id or game_id not in final_goals:
            continue

        goals_map = final_goals[game_id]

        if away_team in goals_map:
            row["away_goals"] = goals_map[away_team]

        if home_team in goals_map:
            row["home_goals"] = goals_map[home_team]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    final_goals = load_final_goals()

    for spreads_file in SPREADS_DIR.glob("nhl_spreads_*.csv"):
        process_spreads_file(spreads_file, final_goals)


if __name__ == "__main__":
    main()
