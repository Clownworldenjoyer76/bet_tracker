#!/usr/bin/env python3
"""
build_edge_ncaab_totals.py (v1)

Purpose:
- Build ONE NCAAB totals (OVER/UNDER) edge pick per game
- Uses Normal distribution with fixed sigma
- Skips low-confidence games

Input:
- docs/win/edge/edge_ncaab_*.csv

Output:
- docs/win/ncaab/edge_ncaab_totals_YYYY_MM_DD.csv
"""

import csv
import glob
from math import erf, sqrt
from pathlib import Path
from datetime import datetime

# =====================
# CONFIG
# =====================
SIGMA = 14.0
BASE_EDGE_BUFFER = 0.07
DISTANCE_PENALTY = 0.06
MIN_MODEL_PROB = 0.55

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/ncaab")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =====================
# HELPERS
# =====================
def normal_cdf(x: float, mu: float, sigma: float) -> float:
    z = (x - mu) / (sigma * sqrt(2))
    return 0.5 * (1 + erf(z))


def fair_decimal(p: float) -> float:
    return 1.0 / p


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def acceptable_decimal(p: float, market_total: float, lam: float) -> float:
    distance = abs(market_total - lam)
    buffer = BASE_EDGE_BUFFER + DISTANCE_PENALTY * distance
    return 1.0 / max(p - buffer, 0.0001)


# =====================
# MAIN
# =====================
def main():
    input_files = sorted(glob.glob(str(INPUT_DIR / "edge_ncaab_*.csv")))
    if not input_files:
        raise FileNotFoundError("No edge_ncaab files found")

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
            game_id = row.get("game_id")
            if not game_id or game_id in seen_games:
                continue

            best_ou = row.get("best_ou")
            if not best_ou:
                continue

            try:
                market_total = float(best_ou)
                lam = float(row["total_points"])
            except Exception:
                continue

            seen_games.add(game_id)

            cutoff = market_total
            p_under = normal_cdf(cutoff, lam, SIGMA)
            p_over = 1.0 - p_under

            if p_over >= p_under:
                side = "OVER"
                model_p = p_over
            else:
                side = "UNDER"
                model_p = p_under

            if model_p < MIN_MODEL_PROB:
                continue

            fair_d = fair_decimal(model_p)
            fair_a = decimal_to_american(fair_d)

            acc_d = acceptable_decimal(model_p, market_total, lam)
            acc_a = decimal_to_american(acc_d)

            writer.writerow({
                "date": row["date"],
                "time": row["time"],
                "team_1": row["team"],
                "team_2": row["opponent"],
                "game_id": game_id,
                "best_ou": market_total,
                "side": side,
                "model_probability": round(model_p, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": fair_a,
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": acc_a,
                "league": "ncaab_ou",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
