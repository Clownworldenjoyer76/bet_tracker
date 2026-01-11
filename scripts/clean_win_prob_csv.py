#!/usr/bin/env python3

import csv
import re
from pathlib import Path

INPUT_DIR = Path("docs/win")
OUTPUT_DIR = INPUT_DIR / "clean"

FILENAME_RE = re.compile(
    r"win_prob_(?P<league>[^_]+)_(?P<date>\d{4}-\d{2}-\d{2})\.csv"
)

OUTPUT_HEADERS = [
    "date",
    "time",
    "team",
    "opponent",
    "win_probability",
    "league",
]

def main():
    if not INPUT_DIR.exists():
        raise RuntimeError("docs/win directory does not exist")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for src in INPUT_DIR.glob("win_prob_*.csv"):
        match = FILENAME_RE.match(src.name)
        if not match:
            continue

        league = match.group("league")
        date = match.group("date")

        dst = OUTPUT_DIR / f"win_prob__clean_{league}_{date}.csv"

        with src.open(newline="", encoding="utf-8") as f_in:
            reader = csv.DictReader(f_in)

            with dst.open("w", newline="", encoding="utf-8") as f_out:
                writer = csv.DictWriter(
                    f_out,
                    fieldnames=OUTPUT_HEADERS
                )
                writer.writeheader()

                for row in reader:
                    writer.writerow({
                        "date": row["date"],
                        "time": row["time"],
                        "team": row["team"],
                        "opponent": row["opponent"],
                        "win_probability": row["win_probability"],
                        "league": row.get("league", league),
                    })

        print(f"Created {dst}")

if __name__ == "__main__":
    main()
