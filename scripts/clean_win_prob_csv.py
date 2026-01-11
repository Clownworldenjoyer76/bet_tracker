#!/usr/bin/env python3

import csv
import re
from pathlib import Path

INPUT_DIR = Path("docs/win")
OUTPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_MAP = {
    "ncaab": "ncaab",
    "nba": "nba",
    "nfl": "nfl",
    "nhl": "nhl",
}


def detect_league(filename: str) -> str:
    name = filename.lower()
    for key in LEAGUE_MAP:
        if key in name:
            return LEAGUE_MAP[key]
    return "unknown"


def is_date_row(row):
    if not row:
        return False
    return bool(re.match(r"\d{2}/\d{2}/\d{4}", row[0]))


def is_header_row(row):
    joined = " ".join(row).lower()
    return "teams" in joined and "win" in joined


def parse():
    for path in INPUT_DIR.glob("win_prob_*.csv"):
        league = detect_league(path.name)

        with path.open(newline="", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        game_date = None
        header_index = None

        # pass 1: find date + header
        for i, row in enumerate(reader):
            if is_date_row(row):
                game_date = row[0].replace("/", "-")
            if is_header_row(row):
                header_index = i
                break

        if not game_date or header_index is None:
            print(f"Skipping {path.name}: unable to detect structure")
            continue

        data_rows = reader[header_index + 1 :]

        cleaned_rows = []

        for row in data_rows:
            if len(row) < 3:
                continue

            time = row[0].strip()
            teams = row[1].strip()
            win = row[2].strip().replace("%", "")

            if " vs " not in teams.lower():
                continue

            team_a, team_b = [t.strip() for t in teams.split(" vs ")]

            try:
                win_prob_a = float(win) / 100.0
                win_prob_b = round(1.0 - win_prob_a, 3)
            except ValueError:
                continue

            cleaned_rows.append(
                {
                    "date": game_date,
                    "time": time,
                    "team": team_a,
                    "opponent": team_b,
                    "win_probability": round(win_prob_a, 3),
                    "league": league,
                }
            )

            cleaned_rows.append(
                {
                    "date": game_date,
                    "time": time,
                    "team": team_b,
                    "opponent": team_a,
                    "win_probability": win_prob_b,
                    "league": league,
                }
            )

        if not cleaned_rows:
            print(f"No games parsed from {path.name}")
            continue

        output_file = OUTPUT_DIR / f"win_prob_clean_{league}_{game_date}.csv"

        with output_file.open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(
                out,
                fieldnames=[
                    "date",
                    "time",
                    "team",
                    "opponent",
                    "win_probability",
                    "league",
                ],
            )
            writer.writeheader()
            writer.writerows(cleaned_rows)

        print(f"Created {output_file}")


def main():
    parse()


if __name__ == "__main__":
    main()
