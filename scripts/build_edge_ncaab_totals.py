#!/usr/bin/env python3
"""
Build NCAAB Totals Edge File (Single Selection, Normal Model)

Inputs:
- docs/win/edge/edge_ncaab_*.csv

Outputs:
- docs/win/ncaab/edge_ncaab_totals_YYYY_MM_DD.csv

Method:
- Normal model using total_points as λ
- σ fixed (configurable)
- Uses best_ou as market line
- Chooses OVER vs UNDER by higher probability
- Skips games with max(model_probability) < 0.55
- Distance-weighted acceptable odds (multiplicative, not inverse)
"""

import csv
import glob
from math import erf, sqrt
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
BASE_EDGE_BUFFER = 0.07
DISTANCE_PENALTY = 0.06
MIN_MODEL_PROB = 0.55
SIGMA = 14.0  # std dev for NCAAB totals

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/ncaab")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normal_cdf(x: float, mu: float, sigma: float) -> float:
    z = (x - mu) / (sigma * sqrt(2))
    return 0.5 * (1 + erf(z))


def fair_decimal(p: float) -> float:
    return 1.0 / p


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def acceptable_decimal(fair_d: float, market_total: float, lam: float) -> float:
    distance = abs(market_total - lam)
    buffer = BASE_EDGE_BUFFER + DISTANCE_PENALTY * distance
    return fair_d * (1.0 + buffer)


def main():
    input_files = sorted(glob.glob(str(INPUT_DIR / "edge_ncaab_*.csv")))
    if not input_files:
        raise FileNotFoundError("No NCAAB edge files found")

    latest_file = input_files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_ncaab_totals_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    seen_games = set()

    with open(latest_file, newline="", encoding="utf-8") as infile, \
         open(out_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = [
            "date",
            "time",
            "team_1",
            "team_2",
            "game_id",
            "best_ou",
            "side",
            "model_probability",
            "fair_decimal_odds",
            "fair_american_odds",
            "acceptable_decimal_odds",
            "acceptable_american_odds",
            "league",
        ]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            try:
                game_id = row["game_id"]
                lam = float(row["total_points"])
                market_total = row.get("best_ou")
                if market_total in ("", None):
                    continue
                market_total = float(market_total)
            except Exception:
                continue

            if game_id in seen_games:
                continue
            seen_games.add(game_id)

            cutoff = market_total

            p_under = normal_cdf(cutoff, lam, SIGMA)
            p_over = 1.0 - p_under

            if p_over >= p_under:
                side = "OVER"
                p = p_over
            else:
                side = "UNDER"
                p = p_under

            if p < MIN_MODEL_PROB:
                continue

            fair_d = fair_decimal(p)
            fair_a = decimal_to_american(fair_d)

            acc_d = acceptable_decimal(fair_d, market_total, lam)
            acc_a = decimal_to_american(acc_d)

            writer.writerow({
                "date": row["date"],
                "time": row["time"],
                "team_1": row["team"],
                "team_2": row["opponent"],
                "game_id": game_id,
                "best_ou": market_total,
                "side": side,
                "model_probability": round(p, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": fair_a,
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": acc_a,
                "league": "ncaab_ou",
            })


if __name__ == "__main__":
    main()
