#!/usr/bin/env python3

import csv
from pathlib import Path

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
CONFIG_PATH = Path("config/nhl/nhl_juice_table.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100 * (decimal - 1)))
    return int(round(-100 / (decimal - 1)))


def load_juice_table():
    rules = []
    with CONFIG_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rules.append({
                "market_type": r["market_type"],
                "low": float(r["band_low"]),
                "high": float(r["band_high"]),
                "side": r["side"],
                "juice": float(r["extra_juice_pct"]),
            })
    return rules


JUICE_RULES = load_juice_table()


def lookup_juice(prob: float) -> float:
    for r in JUICE_RULES:
        if r["market_type"] != "moneyline":
            continue
        if r["low"] <= prob < r["high"]:
            return r["juice"]
    return 0.0


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
            raw_p = (row.get("win_probability") or "").strip()
            if not raw_p:
                row["personally_acceptable_american_odds"] = ""
                writer.writerow(row)
                continue

            p = float(raw_p)
            base_decimal = float(row["acceptable_decimal_odds"])
            base_american = int(row["acceptable_american_odds"])

            edge_pct = lookup_juice(p)
            personal_decimal = base_decimal * (1.0 + edge_pct)
            personal_american = decimal_to_american(personal_decimal)

            # Caps (validated empirically)
            if base_american < 0 and personal_american > 120:
                personal_american = 120

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
