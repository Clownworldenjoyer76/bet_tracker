#!/usr/bin/env python3

import csv
import re
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path("docs/win/dump")
OUTPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE = "soc"

HEADERS = [
    "date",
    "time",
    "team",
    "opponent",
    "goals",
    "total_goals",
    "win_probability",
    "draw_probability",
    "best_ou",
    "league",
]


def strip_team(name: str) -> str:
    if name is None:
        return ""
    s = str(name)
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\s+\d+\s*-\s*\d+\s*$", "", s)
    return s.strip()


def pct_to_decimal(value: str) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s.endswith("%"):
        return str(float(s[:-1]) / 100)
    return s


def parse_best_ou(value: str) -> str:
    if value is None:
        return ""
    match = re.search(r"(\d+)", str(value))
    if not match:
        return ""
    return f"{match.group(1)}.5"


def main():
    files = sorted(INPUT_DIR.glob("soc_*.csv"))
    if not files:
        raise RuntimeError("No input files found")

    for path in files:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Row 0 is header only
        data_rows = rows[1:]

        output_rows = []

        for row in data_rows:
            # column positions are read AS-IS
            # 0 = Time (date \n time)
            # 1 = Teams (teamA \n teamB)
            # 2 = Win (pctA \n pctB)
            # 3 = Draw (single %)
            # 4 = Best ML (ignored)
            # 5 = Goals (goalA \n goalB)
            # 6 = Total Goals
            # 7 = Best O/U

            date_time = row[0].splitlines()
            date = date_time[0] if len(date_time) > 0 else ""
            time = date_time[1] if len(date_time) > 1 else ""

            teams = row[1].splitlines()
            team_a = strip_team(teams[0]) if len(teams) > 0 else ""
            team_b = strip_team(teams[1]) if len(teams) > 1 else ""

            wins = row[2].splitlines()
            win_a = pct_to_decimal(wins[0]) if len(wins) > 0 else ""
            win_b = pct_to_decimal(wins[1]) if len(wins) > 1 else ""

            draw = pct_to_decimal(row[3])

            goals = row[5].splitlines()
            goals_a = goals[0] if len(goals) > 0 else ""
            goals_b = goals[1] if len(goals) > 1 else ""

            total_goals = row[6]
            best_ou = parse_best_ou(row[7])

            output_rows.append([
                date, time,
                team_a, team_b,
                goals_a, total_goals,
                win_a, draw,
                best_ou, LEAGUE
            ])

            output_rows.append([
                date, time,
                team_b, team_a,
                goals_b, total_goals,
                win_b, draw,
                best_ou, LEAGUE
            ])

        # filename date derived from first data row
        file_date = datetime.strptime(
            data_rows[0][0].splitlines()[0],
            "%m/%d/%Y"
        ).strftime("%Y-%m-%d")

        out_path = OUTPUT_DIR / f"win_prob__clean_{LEAGUE}_{file_date}.csv"

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            writer.writerows(output_rows)


if __name__ == "__main__":
    main()
