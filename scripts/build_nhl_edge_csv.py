#!/usr/bin/env python3

import csv
import re
from pathlib import Path

EDGE_DEFAULT = 0.05
EDGE_NHL = 0.08

MIN_P_NHL = 0.52
MIN_EDGE_POS_ODDS_NHL = 0.12
MIN_EDGE_HEAVY_FAV_NHL = 0.35
HEAVY_FAV_THRESHOLD = -250

INPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100.0 * (decimal - 1.0)))
    else:
        return int(round(-100.0 / (decimal - 1.0)))


def normalize_probability(raw: str) -> float:
    p = float(raw)
    if p > 1.0:
        p = p / 100.0
    return p


def normalize_timestamp(ts: str) -> str:
    return re.sub(r"(\d{4})-(\d{2})-(\d{2})", r"\1_\2_\3", ts)


def parse_filename(path: Path):
    parts = [p for p in path.stem.split("_") if p]
    league = parts[-2]
    timestamp = normalize_timestamp(parts[-1])
    return league, timestamp


def process_file(input_path: Path):
    league, timestamp = parse_filename(input_path)

    # HARD GUARANTEE — NHL ONLY
    if league != "nhl":
        return

    output_path = OUTPUT_DIR / f"edge_{league}_{timestamp}.csv"

    with input_path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames) + [
            "fair_decimal_odds",
            "fair_american_odds",
            "acceptable_decimal_odds",
            "acceptable_american_odds",
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            p = normalize_probability(row["win_probability"])
            if not (0.0 < p < 1.0):
                continue

            fair_decimal = 1.0 / p
            fair_american = decimal_to_american(fair_decimal)

            if p < MIN_P_NHL:
                continue

            acceptable_decimal = fair_decimal * (1.0 + EDGE_NHL)
            acceptable_american = decimal_to_american(acceptable_decimal)

            edge = (acceptable_decimal - fair_decimal) / fair_decimal

            if fair_american > 0:
                if edge < MIN_EDGE_POS_ODDS_NHL:
                    continue
            else:
                if fair_american <= HEAVY_FAV_THRESHOLD and edge < MIN_EDGE_HEAVY_FAV_NHL:
                    continue

            row["fair_decimal_odds"] = round(fair_decimal, 6)
            row["fair_american_odds"] = fair_american
            row["acceptable_decimal_odds"] = round(acceptable_decimal, 6)
            row["acceptable_american_odds"] = acceptable_american

            writer.writerow(row)

    print(f"Created {output_path}")


def main():
    # NHL FILES ONLY — NO OTHER LEAGUES CAN BE TOUCHED
    for path in sorted(INPUT_DIR.glob("win_prob__clean_nhl_*.csv")):
        process_file(path)


if __name__ == "__main__":
    main()
