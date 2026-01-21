#!/usr/bin/env python3

import csv
import re
from pathlib import Path

EDGE_NBA = 0.06

INPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100.0 * (decimal - 1.0)))
    return int(round(-100.0 / (decimal - 1.0)))


def normalize_probability(raw: str) -> float:
    p = float(raw)
    if p > 1.0:
        p /= 100.0
    return p


def normalize_timestamp(ts: str) -> str:
    return re.sub(r"(\d{4})-(\d{2})-(\d{2})", r"\1_\2_\3", ts)


def process_file(input_path: Path):
    # NBA ONLY
    if "_nba_" not in input_path.stem:
        return

    timestamp = normalize_timestamp(input_path.stem.split("_")[-1])
    output_path = OUTPUT_DIR / f"edge_nba_{timestamp}.csv"

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
            raw = (row.get("win_probability") or "").strip()

            if not raw:
                row.update({
                    "fair_decimal_odds": "",
                    "fair_american_odds": "",
                    "acceptable_decimal_odds": "",
                    "acceptable_american_odds": "",
                })
                writer.writerow(row)
                continue

            p = normalize_probability(raw)

            if not (0.0 < p < 1.0):
                row.update({
                    "fair_decimal_odds": "",
                    "fair_american_odds": "",
                    "acceptable_decimal_odds": "",
                    "acceptable_american_odds": "",
                })
                writer.writerow(row)
                continue

            fair_decimal = 1.0 / p
            acceptable_decimal = fair_decimal * (1.0 + EDGE_NBA)

            row["fair_decimal_odds"] = round(fair_decimal, 6)
            row["fair_american_odds"] = decimal_to_american(fair_decimal)
            row["acceptable_decimal_odds"] = round(acceptable_decimal, 6)
            row["acceptable_american_odds"] = decimal_to_american(acceptable_decimal)

            writer.writerow(row)

    print(f"Created {output_path}")


def main():
    files = sorted(INPUT_DIR.glob("win_prob__clean_nba_*.csv"))
    if not files:
        raise FileNotFoundError("No NBA clean files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
