#!/usr/bin/env python3

import csv
from pathlib import Path

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def personal_juice(prob: float) -> int:
    """
    Returns extra juice in American odds (integer),
    based on NCAAB personal juice rules.
    """
    if prob >= 0.75:
        return 50   # +50% edge
    if prob >= 0.70:
        return 25   # +25% edge
    if prob >= 0.65:
        return 25   # +25% edge
    if prob >= 0.60:
        return 15   # +15% edge
    if prob >= 0.55:
        return 10   # +10% edge
    if prob >= 0.50:
        return 10   # +10% edge
    if prob >= 0.45:
        return 20   # +20% edge
    if prob >= 0.40:
        return 30   # +30% edge
    if prob >= 0.35:
        return 40   # +40% edge
    return 75       # +75% edge


def process_file(path: Path):
    # edge_ncaab_YYYY_MM_DD.csv → final_ncaab_YYYY_MM_DD.csv
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
            base_acceptable = int(row["acceptable_american_odds"])

            juice = personal_juice(p)
            row["personally_acceptable_american_odds"] = base_acceptable + juice

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
