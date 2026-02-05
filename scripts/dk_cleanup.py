#!/usr/bin/env python3

import csv
import glob
import os
from datetime import datetime
from typing import Dict, Tuple


BASE_DK_PATH = "docs/win/manual/normalized"
BASE_DUMP_PATH = "docs/win/dump/csvs/cleaned"

LEAGUES = ["nba", "ncaab", "nhl"]
MARKETS = {
    "moneyline": "ml",
    "spreads": "spreads",
    "totals": "ou",
}

################################### DATE LOGIC ###################################

def convert_date(date_str: str) -> str:
    """
    Normalize date to YYYY_MM_DD.

    Accepted inputs:
    - MM/DD/YY
    - MM_DD_YYYY
    - YYYY_MM_DD
    """
    # Already correct
    if len(date_str) == 10 and date_str[4] == "_" and date_str[7] == "_":
        return date_str

    # MM/DD/YY
    if "/" in date_str:
        dt = datetime.strptime(date_str, "%m/%d/%y")
        return dt.strftime("%Y_%m_%d")

    # MM_DD_YYYY
    if date_str.count("_") == 2:
        dt = datetime.strptime(date_str, "%m_%d_%Y")
        return dt.strftime("%Y_%m_%d")

    raise ValueError(f"Unrecognized date format: {date_str}")

################################### GAME ID INDEX ###################################

def load_dump_index(league: str) -> Dict[Tuple[str, str], str]:
    """
    Build lookup:
    (date, team) -> game_id
    """
    index: Dict[Tuple[str, str], str] = {}

    pattern = os.path.join(
        BASE_DUMP_PATH,
        f"{league}_*.csv"
    )

    for filepath in glob.glob(pattern):
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game_id = row["game_id"]
                home = row["home_team"]
                away = row["away_team"]

                # Date from filename: league_YYYY_MM_DD.csv
                stem = os.path.basename(filepath).replace(".csv", "")
                _, year, month, day = stem.split("_")
                date = f"{year}_{month}_{day}"

                index[(date, home)] = game_id
                index[(date, away)] = game_id

    return index

################################### DK FILE PROCESSING ###################################

def process_dk_file(
    filepath: str,
    league: str,
    market_suffix: str,
    dump_index: Dict[Tuple[str, str], str],
) -> None:
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not rows:
        return

    if "game_id" not in fieldnames:
        fieldnames.append("game_id")

    new_league_value = f"{league}_{market_suffix}"

    missing_game_ids = []

    for row in rows:
        # league rename
        row["league"] = new_league_value

        # date normalization
        converted_date = convert_date(row["date"])
        row["date"] = converted_date

        # game_id lookup
        team = row["team"]
        game_id = dump_index.get((converted_date, team), "")
        row["game_id"] = game_id

        if not game_id:
            missing_game_ids.append(
                {
                    "file": os.path.basename(filepath),
                    "date": converted_date,
                    "team": team,
                    "league": league,
                    "market": market_suffix,
                }
            )

    if missing_game_ids:
        msg_lines = [
            "ERROR: Missing game_id for DK rows:",
        ]
        for m in missing_game_ids:
            msg_lines.append(
                f"{m['file']} | {m['league']} | {m['market']} | {m['date']} | {m['team']}"
            )
        raise RuntimeError("\n".join(msg_lines))

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

################################### MAIN ###################################

def main() -> None:
    for league in LEAGUES:
        dump_index = load_dump_index(league)

        for market, suffix in MARKETS.items():
            pattern = os.path.join(
                BASE_DK_PATH,
                f"norm_dk_{league}_{market}_*.csv"
            )

            for filepath in glob.glob(pattern):
                process_dk_file(filepath, league, suffix, dump_index)


if __name__ == "__main__":
    main()
