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
    return 1 + (100 / abs(american)))


def personal_edge_pct(prob: float) -> float:
    """
    NBA Personal Juice — v1.0 (All-Time Data Aligned)

    Returns extra edge as a percentage applied multiplicatively
    to acceptable_decimal_odds.
    """
    if prob >= 0.70:
        return 0.15
    if prob >= 0.60:
        return 0.10
    if prob >= 0.55:
        return 0.08
    if prob >= 0.50:
        return 0.08
    if prob >= 0.45:
        return 0.10
    if prob >= 0.40:
        return 0.15
    if prob >= 0.35:
        return 0.20
    if prob >= 0.30:
        return 0.30
    return 0.60


def process_file(path: Path):
    suffix = path.name.replace("edge_nba_", "")
    output_path = OUTPUT_DIR / f"final_nba_{suffix}"

    with path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)

        fieldnames = list(reader.fieldnames) + [
            "personally_acceptable_american_odds",
            "personally_acceptable_decimal_odds",
        ]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            raw_p = (row.get("win_probability") or "").strip()
            if not raw_p:
                row["personally_acceptable_american_odds"] = ""
                row["personally_acceptable_decimal_odds"] = ""
                writer.writerow(row)
                continue

            p = float(raw_p)
            base_decimal = float(row["acceptable_decimal_odds"])
            base_american = int(row["acceptable_american_odds"])

            edge_pct = personal_edge_pct(p)
            personal_decimal = base_decimal * (1.0 + edge_pct)
            personal_american = decimal_to_american(personal_decimal)

            # Cap: favorites may not flip past +120
            if base_american < 0 and personal_american > 120:
                personal_american = 120

            # Cap: extreme tails
            if p < 0.10 and personal_american > 2500:
                personal_american = 2500

            personal_decimal_from_american = american_to_decimal(personal_american)

            row["personally_acceptable_american_odds"] = personal_american
            row["personally_acceptable_decimal_odds"] = round(
                personal_decimal_from_american, 4
            )

            writer.writerow(row)

    print(f"Created {output_path}")


def main():
    files = sorted(INPUT_DIR.glob("edge_nba_*.csv"))
    if not files:
        raise FileNotFoundError("No NBA edge files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
