#!/usr/bin/env python3
"""
scripts/nhl_spreads_01.py

Input:
  docs/win/nhl/edge_nhl_totals_*.csv

Output:
  docs/win/nhl/spreads/nhl_spreads_YYYY_MM_DD.csv

Behavior:
- Reads ALL matching edge_nhl_totals_*.csv files
- Extracts date (YYYY_MM_DD) from the input filename
- For each input file, creates ONE output file
- Copies only the specified columns
- Renames headers exactly as instructed
"""

import csv
from pathlib import Path
import re
import sys

INPUT_DIR = Path("docs/win/nhl")
OUTPUT_DIR = INPUT_DIR / "spreads"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = [
    "game_id",
    "date",
    "time",
    "team_1",
    "team_2",
    "market_total",
    "side",
    "model_probability",
]

HEADER_MAP = {
    "team_1": "away_team",
    "team_2": "home_team",
    "model_probability": "ou_prob",
}


def extract_date_from_filename(filename: str) -> str:
    """
    Expects edge_nhl_totals_YYYY_MM_DD*.csv
    Returns YYYY_MM_DD
    """
    match = re.search(r"(\d{4}_\d{2}_\d{2})", filename)
    if not match:
        raise ValueError(f"Could not extract date from filename: {filename}")
    return match.group(1)


def process_file(path: Path):
    date_str = extract_date_from_filename(path.name)
    output_path = OUTPUT_DIR / f"nhl_spreads_{date_str}.csv"

    with path.open(newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)

        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path.name} missing required columns: {missing}")

        output_headers = [
            HEADER_MAP.get(col, col) for col in REQUIRED_COLUMNS
        ]

        with output_path.open("w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_headers)
            writer.writeheader()

            for row in reader:
                out_row = {}
                for col in REQUIRED_COLUMNS:
                    out_col = HEADER_MAP.get(col, col)
                    out_row[out_col] = row[col]
                writer.writerow(out_row)

    print(f"Created: {output_path}")


def main():
    files = sorted(INPUT_DIR.glob("edge_nhl_totals_*.csv"))

    if not files:
        print("No input files found.", file=sys.stderr)
        sys.exit(1)

    for f in files:
        process_file(f)


if __name__ == "__main__":
    main()
