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
    if len(date_str) == 10 and date_str[4] == "_" and date_str[7] == "_":
        return date_str

    if "/" in date_str:
        dt = datetime.strptime(date_str, "%m/%d/%y")
        return dt.strftime("%Y_%m_%d")

    if date_str.count("_") == 2:
        dt = datetime.strptime(date_str, "%m_%d_%Y")
        return dt.strftime("%Y_%m_%d")

    raise ValueError(f"Unrecognized date format: {date_str}")

################################### GAME ID INDEX ###################################

def load_dump_index(league: str) -> Dict[Tuple[str, str], str]:
    index: Dict[Tuple[str, str], str] = {}

    pattern = os.path.join(BASE_DUMP_PATH, f"{league}_*.csv")

    for filepath in glob.glob(pattern):
        stem = os.path.basename(filepath).replace(".csv", "")
        _, year, month, day = stem.split("_")
        date = f"{year}_{month}_{day}"

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game_id = row["game_id"]
                index[(date, row["home_team"])] = game_id
                index[(date, row["away_team"])] = game_id

    return index

################################### DK FILE PROCESSING ###################################

def process_dk_file(filepath, league, market_suffix, dump_index):
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not rows:
        return

    if "game_id" not in fieldnames:
        fieldnames.append("game_id")

    new_league_value = f"{league}_{market_suffix}"
    missing = []

    for row in rows:
        row["league"] = new_league_value
        date = convert_date(row["date"])
        row["date"] = date

        team = row["team"]
        game_id = dump_index.get((date, team), "")
        row["game_id"] = game_id

        if not game_id:
            missing.append((os.path.basename(filepath), league, market_suffix, date, team))

    if missing:
        lines = ["ERROR: Missing game_id for DK rows:"]
        for m in missing:
            lines.append(f"{m[0]} | {m[1]} | {m[2]} | {m[3]} | {m[4]}")
        raise RuntimeError("\n".join(lines))

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

################################### MAIN ###################################

def main():
    for league in LEAGUES:
        dump_index = load_dump_index(league)

        for market, suffix in MARKETS.items():
            pattern = os.path.join(BASE_DK_PATH, f"norm_dk_{league}_{market}_*.csv")
            for filepath in glob.glob(pattern):
                process_dk_file(filepath, league, suffix, dump_index)

if __name__ == "__main__":
    main()
