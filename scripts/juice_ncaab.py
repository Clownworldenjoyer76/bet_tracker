#!/usr/bin/env python3

import csv
from pathlib import Path

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100 * (decimal - 1)))
    return int(round(-100 / (decimal - 1)))


def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1 + (american / 100)
    return 1 + (100 / abs(american))



def personal_edge_pct(prob: float) -> float:
    """
    Returns personal juice as a percentage (e.g. 0.20 = 20%)
    applied multiplicatively to acceptable_decimal_odds.
    NCAAB v1.2 — all-time data aligned
    """

    if prob >= 0.75:
        return 0.25   # ↓ reduced from 0.30
    if prob >= 0.70:
        return 0.20   # ↓ reduced from 0.25
    if prob >= 0.65:
        return 0.15   # ↓ reduced from 0.25
    if prob >= 0.60:
        return 0.10   # unchanged
    if prob >= 0.55:
        return 0.05   # unchanged (best-performing zone)
    if prob >= 0.50:
        return 0.05   # ↓ reduced from 0.10
    if prob >= 0.45:
        return 0.15   # ↓ reduced from 0.20
    if prob >= 0.40:
        return 0.25   # ↓ reduced from 0.30
    if prob >= 0.35:
        return 0.35   # ↓ reduced from 0.40
    return 0.75       # unchanged (extreme tail protection)



def process_file(path: Path):
    suffix = path.name.replace("edge_ncaab_", "")
    output_path = OUTPUT_DIR / f"final_ncaab_{suffix}"

    with path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames) + [
            "personally_acceptable_american_odds"
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            p = float(row["win_probability"])
            base_decimal = float(row["acceptable_decimal_odds"])
            base_american = int(row["acceptable_american_odds"])

            edge_pct = personal_edge_pct(p)
            personal_decimal = base_decimal * (1.0 + edge_pct)
            personal_american = decimal_to_american(personal_decimal)

            # RULE 1: cap favorite flip-through
            if base_american < 0 and personal_american > 120:
                personal_american = 120

            # RULE 2: cap extreme longshots
            if p < 0.10 and personal_american > 2500:
                personal_american = 2500

            row["personally_acceptable_american_odds"] = personal_american
            writer.writerow(row)

    print(f"Created {output_path}")



def main():
    files = sorted(INPUT_DIR.glob("edge_ncaab_*.csv"))
    if not files:
        raise FileNotFoundError("No NCAAB edge files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
