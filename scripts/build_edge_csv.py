#!/usr/bin/env python3

import csv
import re
from pathlib import Path

EDGE = 0.05          # default edge buffer for non-soc leagues
SOC_EDGE = 0.15      # stricter buffer for 3-way soccer markets

INPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100.0 * (decimal - 1.0)))
    else:
        return int(round(-100.0 / (decimal - 1.0)))


def normalize_probability(raw: str) -> float:
    p = float(raw)
    if p > 1.0:
        p = p / 100.0
    return p


def normalize_timestamp(ts: str) -> str:
    ts = re.sub(r"(\d{4})-(\d{2})-(\d{2})", r"\1_\2_\3", ts)
    return ts


def parse_filename(path: Path):
    name = path.stem
    parts = [p for p in name.split("_") if p != ""]

    if len(parts) < 4:
        raise ValueError(f"Unexpected filename format: {path.name}")

    league = parts[-2]
    timestamp = normalize_timestamp(parts[-1])
    return league, timestamp


def derive_draw_probability(p1: float, p2: float) -> float:
    p_draw = 1.0 - (p1 + p2)
    if not (0.0 <= p_draw <= 0.4):
        raise ValueError(f"Invalid derived draw probability: {p_draw}")
    return p_draw


def process_file(input_path: Path):
    league, timestamp = parse_filename(input_path)
    output_path = OUTPUT_DIR / f"edge_{league}_{timestamp}.csv"

    with input_path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        if not reader.fieldnames or "win_probability" not in reader.fieldnames:
            raise ValueError(f"{input_path.name} missing required 'win_probability' column")

        # preserve all input columns (including best_ou if present)
        fieldnames = list(reader.fieldnames) + [
            "fair_decimal_odds",
            "fair_american_odds",
            "acceptable_decimal_odds",
            "acceptable_american_odds",
        ]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        rows = list(reader)

        # ---- SOC ONLY LOGIC ----
        if league == "soc":
            games = {}
            for row in rows:
                game_id = row.get("game_id")
                if not game_id:
                    continue
                games.setdefault(game_id, []).append(row)

            for game_id, game_rows in games.items():
                if len(game_rows) != 2:
                    continue

                r1, r2 = game_rows
                p1 = normalize_probability(r1["win_probability"])
                p2 = normalize_probability(r2["win_probability"])

                if not (0.0 < p1 < 1.0 and 0.0 < p2 < 1.0):
                    continue

                p_draw = derive_draw_probability(p1, p2)

                if p_draw > 0.28:
                    continue

                for row, p_win in [(r1, p1), (r2, p2)]:
                    p_conditional = p_win / (1.0 - p_draw)

                    fair_decimal = 1.0 / p_conditional
                    acceptable_decimal = fair_decimal * SOC_EDGE

                    row["fair_decimal_odds"] = round(fair_decimal, 6)
                    row["fair_american_odds"] = decimal_to_american(fair_decimal)
                    row["acceptable_decimal_odds"] = round(acceptable_decimal, 6)
                    row["acceptable_american_odds"] = decimal_to_american(acceptable_decimal)

                    writer.writerow(row)

        # ---- ALL OTHER LEAGUES (UNCHANGED) ----
        else:
            for row in rows:
                p = normalize_probability(row["win_probability"])

                if not (0.0 < p < 1.0):
                    continue

                fair_decimal = 1.0 / p
                acceptable_decimal = fair_decimal * (1.0 + EDGE)

                row["fair_decimal_odds"] = round(fair_decimal, 6)
                row["fair_american_odds"] = decimal_to_american(fair_decimal)
                row["acceptable_decimal_odds"] = round(acceptable_decimal, 6)
                row["acceptable_american_odds"] = decimal_to_american(acceptable_decimal)

                writer.writerow(row)

    print(f"Created {output_path}")


def main():
    input_files = sorted(INPUT_DIR.glob("win_prob__clean_*.csv"))

    if not input_files:
        raise FileNotFoundError(
            f"No cleaned files found in {INPUT_DIR} matching win_prob__clean_*.csv"
        )

    for path in input_files:
        process_file(path)


if __name__ == "__main__":
    main()
