#!/usr/bin/env python3

import csv
import re
from pathlib import Path

# Market vig baseline (house juice)
EDGE = 0.05  # 5% market vig approximation

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
    if len(parts) < 4:
        raise ValueError(f"Unexpected filename format: {path.name}")
    return parts[-2], normalize_timestamp(parts[-1])


def process_file(input_path: Path):
    league, timestamp = parse_filename(input_path)
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

            # Fair odds from model
            fair_decimal = 1.0 / p
            fair_american = decimal_to_american(fair_decimal)

            # Market-vig baseline (house juice only)
            acceptable_decimal = fair_decimal * (1.0 + EDGE)
            acceptable_american = decimal_to_american(acceptable_decimal)

            row["fair_decimal_odds"] = round(fair_decimal, 6)
            row["fair_american_odds"] = fair_american
            row["acceptable_decimal_odds"] = round(acceptable_decimal, 6)
            row["acceptable_american_odds"] = acceptable_american

            writer.writerow(row)

    print(f"Created {output_path}")


def main():
    files = sorted(INPUT_DIR.glob("win_prob__clean_ncaab_*"))
    if not files:
        raise FileNotFoundError("No cleaned NCAAB files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
