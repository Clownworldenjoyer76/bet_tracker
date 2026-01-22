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


def personal_edge_pct(prob: float) -> float:
    """
    NHL v1.0 — all-time data aligned
    Returns personal juice as a percentage applied multiplicatively
    to acceptable_decimal_odds.
    """

    if prob >= 0.70:
        return 0.15
    if prob >= 0.65:
        return 0.10
    if prob >= 0.60:
        return 0.08   # cleanest zone (matches legacy EDGE_NHL)
    if prob >= 0.55:
        return 0.10
    if prob >= 0.50:
        return 0.15
    if prob >= 0.45:
        return 0.10
    if prob >= 0.40:
        return 0.20
    if prob >= 0.35:
        return 0.30
    if prob >= 0.30:
        return 0.40
    return 0.75       # p < 0.30 — extreme tail protection


def process_file(path: Path):
    suffix = path.name.replace("edge_nhl_", "")
    output_path = OUTPUT_DIR / f"final_nhl_{suffix}"

    with path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames) + [
            "personally_acceptable_american_odds"
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            raw_p = row.get("win_probability", "").strip()
            if not raw_p:
                row["personally_acceptable_american_odds"] = ""
                writer.writerow(row)
                continue

            p = float(raw_p)
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
    files = sorted(INPUT_DIR.glob("edge_nhl_*.csv"))
    if not files:
        raise FileNotFoundError("No NHL edge files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
