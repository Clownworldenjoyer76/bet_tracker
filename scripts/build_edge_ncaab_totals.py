#!/usr/bin/env python3
"""
Build NCAAB Totals Edge File (Normal Model, Single Selection)

Inputs:
- docs/win/edge/edge_ncaab_*.csv

Outputs:
- docs/win/ncaab/edge_ncaab_totals_YYYY_MM_DD.csv

Rules:
- Uses total_points as λ
- Normal approximation
- Chooses OVER vs UNDER by higher model probability
- Skips game if max(model_probability) < 0.55
- One row per game
"""

import csv
import glob
from math import erf, sqrt
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
BASE_EDGE_BUFFER = 0.07
DISTANCE_PENALTY = 0.15  # increased distance sensitivity
STD_DEV = 11.0  # fixed total-points std dev

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


def acceptable_decimal(p: float, market_total: float, lam: float) -> float:
    distance = abs(market_total - lam)
    buffer = BASE_EDGE_BUFFER + DISTANCE_PENALTY * distance
    return 1.0 / max(p - buffer, 0.0001)


def main():
    files = sorted(glob.glob(str(INPUT_DIR / "edge_ncaab_*.csv")))
    if not files:
        raise FileNotFoundError("No NCAAB edge files found")

    latest = files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_ncaab_totals_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    seen = set()

    with open(latest, newline="", encoding="utf-8") as infile, \
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
                market = row.get("best_ou")
                if not market:
                    continue
                market = float(market)
            except Exception:
                continue

            if game_id in seen:
                continue
            seen.add(game_id)

            cutoff = market - 0.5
            p_under = normal_cdf(cutoff, lam, STD_DEV)
            p_over = 1.0 - p_under

            if max(p_under, p_over) < 0.55:
                continue

            if p_over >= p_under:
                side = "OVER"
                p = p_over
            else:
                side = "UNDER"
                p = p_under

            fair_d = fair_decimal(p)
            fair_a = decimal_to_american(fair_d)

            acc_d = acceptable_decimal(p, market, lam)
            acc_a = decimal_to_american(acc_d)

            writer.writerow({
                "date": row["date"],
                "time": row["time"],
                "team_1": row["team"],
                "team_2": row["opponent"],
                "game_id": game_id,
                "best_ou": market,
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
