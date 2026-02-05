#!/usr/bin/env python3

import csv
import glob
import os
from datetime import datetime
from typing import Dict, Tuple


BASE_DK_PATH = "docs/win/manual/normalized"
BASE_JUICE_PATH = "docs/win/juice"

LEAGUES = ["nba", "ncaab", "nhl"]
MARKETS = {
    "moneyline": "ml",
    "spreads": "spreads",
    "totals": "ou",
}

###################################DATE LOGIC###########################################################

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

###########################################



def load_juice_index(league: str, market: str) -> Dict[Tuple[str, str], str]:
    """
    Build lookup:
    (date, team) -> game_id
    """
    index = {}

    pattern = os.path.join(
        BASE_JUICE_PATH,
        league,
        market,
        f"juice_{league}_{market}_*.csv"
    )

    for filepath in glob.glob(pattern):
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["date"]
                game_id = row["game_id"]

                home = row["home_team"]
                away = row["away_team"]

                index[(date, home)] = game_id
                index[(date, away)] = game_id

    return index


def process_dk_file(
    filepath: str,
    league: str,
    market_suffix: str,
    juice_index: Dict[Tuple[str, str], str],
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

    for row in rows:
        # league rename
        row["league"] = new_league_value

        # date conversion
        original_date = row["date"]
        converted_date = convert_date(original_date)
        row["date"] = converted_date

        # game_id lookup (use converted date)
        team = row["team"]
        row["game_id"] = juice_index.get((converted_date, team), "")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    for league in LEAGUES:
        for market, suffix in MARKETS.items():
            juice_index = load_juice_index(league, market)

            pattern = os.path.join(
                BASE_DK_PATH,
                f"norm_dk_{league}_{market}_*.csv"
            )

            for filepath in glob.glob(pattern):
                process_dk_file(filepath, league, suffix, juice_index)


if __name__ == "__main__":
    main()
