#!/usr/bin/env python3

import csv
from pathlib import Path

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
CONFIG_PATH = Path("config/nba/nba_juice_table.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100 * (decimal - 1)))
    return int(round(-100 / (decimal - 1)))


def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1 + (american / 100)
    return 1 + (100 / abs(american)))


# ---------------------------------------------------------------------
# Load NBA juice config (moneyline only)
# ---------------------------------------------------------------------
def load_moneyline_juice_table():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing juice config: {CONFIG_PATH}")

    rules = []

    with CONFIG_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required_cols = {
            "market_type",
            "band_low",
            "band_high",
            "side",
            "extra_juice_pct",
        }

        if not required_cols.issubset(reader.fieldnames):
            raise ValueError(
                f"Config schema invalid. Required columns: {required_cols}"
            )

        for row in reader:
            if row["market_type"] != "moneyline":
                continue

            rules.append({
                "low": float(row["band_low"]),
                "high": float(row["band_high"]),
                "side": row["side"].strip().lower(),  # any / favorite / underdog
                "juice": float(row["extra_juice_pct"]),
            })

    if not rules:
        raise ValueError("No moneyline rules found in juice table")

    return rules


ML_JUICE_RULES = load_moneyline_juice_table()


def lookup_edge_pct(prob: float, side: str) -> float:
    """
    side: 'favorite' | 'underdog'
    """
    for r in ML_JUICE_RULES:
        if r["low"] <= prob < r["high"]:
            if r["side"] == "any" or r["side"] == side:
                return r["juice"]

    raise ValueError(f"No juice rule matched for p={prob}, side={side}")


# ---------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------
def process_file(path: Path):
    suffix = path.name.replace("edge_nba_", "")
    output_path = OUTPUT_DIR / f"final_nba_{suffix}"

    with path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)

        required = {
            "win_probability",
            "acceptable_decimal_odds",
            "acceptable_american_odds",
            "side",  # favorite / underdog
        }

        if not required.issubset(reader.fieldnames):
            raise ValueError(
                f"{path.name} missing required columns: {required}"
            )

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
            side = row["side"].strip().lower()

            base_decimal = float(row["acceptable_decimal_odds"])
            base_american = int(row["acceptable_american_odds"])

            edge_pct = lookup_edge_pct(p, side)

            personal_decimal = base_decimal * (1.0 + edge_pct)
            personal_american = decimal_to_american(personal_decimal)

            # --------------------------------------------------
            # Safety caps (unchanged logic)
            # --------------------------------------------------
            if base_american < 0 and personal_american > 120:
                personal_american = 120

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
