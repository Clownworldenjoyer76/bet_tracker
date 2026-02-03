#!/usr/bin/env python3

import csv
from pathlib import Path

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
CONFIG_PATH = Path("config/nba/nba_juice_table.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------- Odds helpers ----------

def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100 * (decimal - 1)))
    return int(round(-100 / (decimal - 1)))


def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1 + (american / 100)
    return 1 + (100 / abs(american))


# ---------- Load juice config ----------

def load_moneyline_juice_table():
    """
    Loads NBA moneyline juice rules from config CSV.
    Returns ordered list of dicts.
    """
    rules = []

    with CONFIG_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["market_type"] != "moneyline":
                continue

            rules.append({
                "low": float(row["band_low"]),
                "high": float(row["band_high"]),
                "side": row["side"],
                "extra": float(row["extra_juice_pct"]),
            })

    # Highest probability first (defensive ordering)
    rules.sort(key=lambda r: r["low"], reverse=True)
    return rules


JUICE_RULES = load_moneyline_juice_table()


def lookup_personal_edge(prob: float) -> float:
    """
    Returns extra juice pct based on win_probability.
    """
    for rule in JUICE_RULES:
        if rule["low"] <= prob < rule["high"]:
            return rule["extra"]
    return 0.0


# ---------- Main processing ----------

def process_file(path: Path):
    suffix = path.name.replace("edge_nba_", "")
    output_path = OUTPUT_DIR / f"final_nba_{suffix}"

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

            edge_pct = lookup_personal_edge(p)

            personal_decimal = base_decimal * (1.0 + edge_pct)
            personal_american = decimal_to_american(personal_decimal)

            # ----- Guards -----

            # Favorites may not flip into absurd dogs
            if base_american < 0 and personal_american > 120:
                personal_american = 120

            # Extreme tail protection
            if p < 0.10 and personal_american > 2500:
                personal_american = 2500

            row["personally_acceptable_american_odds"] = personal_american
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
