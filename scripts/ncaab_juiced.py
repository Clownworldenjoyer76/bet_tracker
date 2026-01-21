#!/usr/bin/env python3

import csv
from pathlib import Path

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def personal_juice(prob: float) -> int | None:
    """
    Returns extra juice in American odds (positive integer),
    or None to indicate NO BET.
    """
    if prob >= 0.75:
        return int(round(0.50 * 100))   # +50% edge
    if prob >= 0.70:
        return int(round(0.25 * 100))   # +25% edge
    if prob >= 0.65:
        return int(round(0.25 * 100))   # +25% edge
    if prob >= 0.60:
        return int(round(0.15 * 100))   # +15% edge
    if prob >= 0.55:
        return int(round(0.10 * 100))   # +10% edge
    if prob >= 0.50:
        return int(round(0.10 * 100))   # +10% edge
    return None  # p < 0.50 → NO BET


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

            if juice is None:
                row["personally_acceptable_american_odds"] = ""
            else:
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
