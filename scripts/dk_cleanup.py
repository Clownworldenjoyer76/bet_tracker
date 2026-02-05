#!/usr/bin/env python3

import csv
import glob
import os
from datetime import datetime


BASE_PATH = "docs/win/manual/normalized"

LEAGUES = ["nba", "ncaab", "nhl"]
MARKETS = {
    "moneyline": "ml",
    "spreads": "spreads",
    "totals": "ou",
}


def convert_date(date_str: str) -> str:
    """
    Convert MM/DD/YY -> MM_DD_YYYY
    Example: 02/04/26 -> 02_04_2026
    """
    dt = datetime.strptime(date_str, "%m/%d/%y")
    return dt.strftime("%m_%d_%Y")


def process_file(filepath: str, league: str, market_suffix: str) -> None:
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        return

    new_league_value = f"{league}_{market_suffix}"

    for row in rows:
        if "league" in row:
            row["league"] = new_league_value

        if "date" in row and row["date"]:
            row["date"] = convert_date(row["date"])

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    for league in LEAGUES:
        for market, suffix in MARKETS.items():
            pattern = os.path.join(
                BASE_PATH,
                f"norm_dk_{league}_{market}_*.csv"
            )

            for filepath in glob.glob(pattern):
                process_file(filepath, league, suffix)


if __name__ == "__main__":
    main()
