#!/usr/bin/env python3

import csv
from pathlib import Path

FINAL_DIR = Path("docs/win/final")


def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1 + (american / 100)
    return 1 + (100 / abs(american))


def process_file(path: Path):
    tmp_path = path.with_suffix(".tmp")

    with path.open(newline="", encoding="utf-8") as infile, \
         tmp_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)

        if "personally_acceptable_decimal_odds" not in fieldnames:
            fieldnames.append("personally_acceptable_decimal_odds")

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            raw_american = (row.get("personally_acceptable_american_odds") or "").strip()

            if raw_american == "":
                row["personally_acceptable_decimal_odds"] = ""
            else:
                american = int(raw_american)
                decimal = american_to_decimal(american)
                row["personally_acceptable_decimal_odds"] = round(decimal, 6)

            writer.writerow(row)

    tmp_path.replace(path)
    print(f"Updated {path.name}")


def main():
    files = sorted(FINAL_DIR.glob("final_*.csv"))
    if not files:
        raise FileNotFoundError("No final_*.csv files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
