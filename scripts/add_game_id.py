#!/usr/bin/env python3

import csv
from pathlib import Path
from datetime import datetime

PATTERN = "docs/win/clean/win_prob__clean_*.csv"


def is_empty(value):
    return value is None or value == ""


def process_file(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "game_id" not in fieldnames:
        fieldnames.append("game_id")
        for row in rows:
            row["game_id"] = ""

    game_counter = 1
    total_rows = len(rows)

    for i in range(total_rows):
        row_a = rows[i]

        if not is_empty(row_a.get("game_id")):
            continue

        team_a = row_a.get("team")
        opp_a = row_a.get("opponent")

        for j in range(i + 1, total_rows):
            row_b = rows[j]

            if not is_empty(row_b.get("game_id")):
                continue

            if row_b.get("team") == opp_a and row_b.get("opponent") == team_a:
                league = row_a.get("league")
                raw_date = row_a.get("date")

                try:
                    dt = datetime.strptime(raw_date, "%m/%d/%Y")
                except ValueError:
                    dt = datetime.strptime(raw_date, "%m/%d/%y")

                formatted_date = dt.strftime("%Y_%m_%d")

                game_id = f"{league}_{formatted_date}_game_{game_counter}"

                row_a["game_id"] = game_id
                row_b["game_id"] = game_id

                game_counter += 1
                break

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    for path in sorted(Path().glob(PATTERN)):
        process_file(path)


if __name__ == "__main__":
    main()
