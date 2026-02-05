#!/usr/bin/env python3
#scripts/dk_cleanup.py

import csv
import glob
import os
import re
import pandas as pd
from datetime import datetime
from typing import Dict, Tuple


BASE_DK_PATH = "docs/win/manual/normalized"
BASE_DUMP_PATH = "docs/win/dump/csvs/cleaned"
TEAM_MAP_PATH = "mappings/team_map.csv"

LEAGUES = ["nba", "ncaab", "nhl"]
MARKETS = {
    "moneyline": "ml",
    "spreads": "spreads",
    "totals": "ou",
}

################################### NORMALIZATION ###################################

def norm(s: str) -> str:
    if s is None:
        return s
    s = str(s).replace("\u00A0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def load_team_map() -> Dict[str, Dict[str, str]]:
    """
    league -> {dk_team: canonical_team}
    """
    df = pd.read_csv(TEAM_MAP_PATH, dtype=str)

    df["league"] = df["league"].str.lower()
    df["dk_team"] = df["dk_team"].apply(norm)
    df["canonical_team"] = df["canonical_team"].apply(norm)

    team_map: Dict[str, Dict[str, str]] = {}
    for _, r in df.iterrows():
        lg = r["league"]
        dk = r["dk_team"]
        can = r["canonical_team"]
        if pd.isna(lg) or pd.isna(dk) or pd.isna(can):
            continue
        team_map.setdefault(lg, {})[dk] = can

    return team_map

################################### DATE LOGIC ###################################

def convert_date(date_str: str) -> str:
    """
    Normalize date to YYYY_MM_DD.

    Accepted inputs:
    - MM/DD/YY
    - MM_DD_YYYY
    - YYYY_MM_DD
    """
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

def load_dump_index(
    league: str,
    team_map: Dict[str, Dict[str, str]],
) -> Dict[Tuple[str, str], str]:
    """
    Build lookup:
    (date, canonical_team) -> game_id
    """
    index: Dict[Tuple[str, str], str] = {}

    pattern = os.path.join(
        BASE_DUMP_PATH,
        f"{league}_*.csv"
    )

    league_team_map = team_map.get(league, {})

    for filepath in glob.glob(pattern):
        stem = os.path.basename(filepath).replace(".csv", "")
        parts = stem.split("_")

        if len(parts) < 4:
            raise ValueError(f"Unexpected dump filename format: {filepath}")

        year, month, day = parts[-3:]
        date = f"{year}_{month}_{day}"

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game_id = row["game_id"]

                home_raw = norm(row["home_team"])
                away_raw = norm(row["away_team"])

                home = league_team_map.get(home_raw, home_raw)
                away = league_team_map.get(away_raw, away_raw)

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
        row["league"] = new_league_value

        converted_date = convert_date(row["date"])
        row["date"] = converted_date

        team = norm(row["team"])
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
        msg_lines = ["ERROR: Missing game_id for DK rows:"]
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
    team_map = load_team_map()

    for league in LEAGUES:
        dump_index = load_dump_index(league, team_map)

        for market, suffix in MARKETS.items():
            pattern = os.path.join(
                BASE_DK_PATH,
                f"norm_dk_{league}_{market}_*.csv"
            )

            for filepath in glob.glob(pattern):
                process_dk_file(filepath, league, suffix, dump_index)


if __name__ == "__main__":
    main()
