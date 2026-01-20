#!/usr/bin/env python3

import csv
import re
from pathlib import Path

EDGE = 0.05
NCAAB_MIN_EDGE = 0.10          # ≥ +10%
NCAAB_MIN_PROB = 0.50          # win probability floor
NCAAB_DOG_MIN_PROB = 0.45      # underdog floor
NCAAB_DOG_MIN_EDGE = 0.15      # underdog edge
NCAAB_HEAVY_FAV_LINE = -300
NCAAB_HEAVY_FAV_EDGE = 0.50    # ≥ +50%

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

            fair_decimal = 1.0 / p
            fair_american = decimal_to_american(fair_decimal)

            # -------- NCAAB RULES --------
            if league == "ncaab":
                edge_required = NCAAB_MIN_EDGE

                if fair_american > 0:
                    if p < NCAAB_DOG_MIN_PROB:
                        continue
                    edge_required = max(edge_required, NCAAB_DOG_MIN_EDGE)

                if fair_american <= NCAAB_HEAVY_FAV_LINE:
                    edge_required = max(edge_required, NCAAB_HEAVY_FAV_EDGE)

                if p < NCAAB_MIN_PROB:
                    continue

                acceptable_decimal = fair_decimal * (1.0 + edge_required)

            # -------- ALL OTHER LEAGUES --------
            else:
                acceptable_decimal = fair_decimal * (1.0 + EDGE)

            row["fair_decimal_odds"] = round(fair_decimal, 6)
            row["fair_american_odds"] = fair_american
            row["acceptable_decimal_odds"] = round(acceptable_decimal, 6)
            row["acceptable_american_odds"] = decimal_to_american(acceptable_decimal)

            writer.writerow(row)

    print(f"Created {output_path}")


def main():
    files = sorted(INPUT_DIR.glob("win_prob__clean_*.csv"))
    if not files:
        raise FileNotFoundError("No cleaned files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
