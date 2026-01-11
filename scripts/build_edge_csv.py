#!/usr/bin/env python3

import csv
from pathlib import Path

EDGE = 0.05  # requires 5% better price than fair odds

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


def parse_filename(path: Path):
    """
    Expected filename:
      win_prob__clean_{league}_{timestamp}.csv
    """
    name = path.stem
    parts = name.split("_")
    if len(parts) < 5:
        raise ValueError(f"Unexpected filename format: {path.name}")

    league = parts[-2]
    timestamp = parts[-1]
    return league, timestamp


def process_file(input_path: Path):
    league, timestamp = parse_filename(input_path)
    output_path = OUTPUT_DIR / f"edge_{league}_{timestamp}.csv"

    with input_path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        if not reader.fieldnames or "win_probability" not in reader.fieldnames:
            raise ValueError(f"{input_path.name} missing required 'win_probability' column")

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
                raise ValueError(
                    f"Invalid win_probability '{row['win_probability']}' in {input_path.name}"
                )

            fair_decimal = 1.0 / p
            acceptable_decimal = fair_decimal * (1.0 + EDGE)

            row["fair_decimal_odds"] = round(fair_decimal, 6)
            row["fair_american_odds"] = decimal_to_american(fair_decimal)
            row["acceptable_decimal_odds"] = round(acceptable_decimal, 6)
            row["acceptable_american_odds"] = decimal_to_american(acceptable_decimal)

            writer.writerow(row)

    print(f"Created {output_path}")


def main():
    input_files = sorted(INPUT_DIR.glob("win_prob__clean_*.csv"))

    if not input_files:
        raise FileNotFoundError(
            f"No cleaned files found in {INPUT_DIR} matching win_prob__clean_*.csv"
        )

    for path in input_files:
        process_file(path)


if __name__ == "__main__":
    main()
