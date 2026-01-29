#!/usr/bin/env python3

import csv
from pathlib import Path

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/ncaab/ncaab_ml_juice_table.csv")

# -------------------------------------------------
# ODDS HELPERS
# -------------------------------------------------

def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100 * (decimal - 1)))
    return int(round(-100 / (decimal - 1)))


def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1 + (american / 100)
    return 1 + (100 / abs(american))


# -------------------------------------------------
# LOAD PERSONAL ML JUICE TABLE
# -------------------------------------------------

def load_ml_juice_table(path: Path):
    table = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["market_type"] != "moneyline":
                continue

            table.append({
                "low": float(row["band_low"]),
                "high": float(row["band_high"]),
                "juice": float(row["extra_juice_pct"]),
            })
    return table


ML_JUICE_TABLE = load_ml_juice_table(JUICE_TABLE_PATH)


def lookup_ml_juice(prob: float) -> float:
    """
    Returns personal juice pct based on model probability.
    """
    for r in ML_JUICE_TABLE:
        if r["low"] <= prob < r["high"]:
            return r["juice"]
    return 0.0


# -------------------------------------------------
# CORE PROCESSOR
# -------------------------------------------------

def process_file(path: Path):
    suffix = path.name.replace("edge_ncaab_", "")
    output_path = OUTPUT_DIR / f"final_ncaab_{suffix}"

    with path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)

        if "win_probability" not in reader.fieldnames:
            raise ValueError("This script is moneyline-only")

        fieldnames = list(reader.fieldnames) + [
            "personally_acceptable_american_odds"
        ]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            p = float(row["win_probability"])
            base_decimal = float(row["acceptable_decimal_odds"])
            base_american = int(row["acceptable_american_odds"])

            edge_pct = lookup_ml_juice(p)

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


# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    files = sorted(INPUT_DIR.glob("edge_ncaab_*.csv"))
    if not files:
        raise FileNotFoundError("No NCAAB edge files found")

    for path in files:
        process_file(path)


if __name__ == "__main__":
    main()
