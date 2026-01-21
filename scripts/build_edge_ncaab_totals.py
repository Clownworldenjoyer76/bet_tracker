#!/usr/bin/env python3
"""
Build NCAAB Totals Edge File (Normal Model, Single Selection)

Inputs:
- docs/win/edge/edge_ncaab_*.csv

Outputs:
- docs/win/ncaab/edge_ncaab_totals_YYYY_MM_DD.csv

Rules:
- λ derived from total_points
- Normal model for totals
- Skip games with no best_ou
- Skip if max(model_probability) < 0.55
- Select OVER or UNDER with higher probability
- ONE output row per game
"""

import csv
import glob
from math import sqrt, erf
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
BASE_EDGE_BUFFER = 0.07
DISTANCE_PENALTY = 0.08   # ← UPDATED
MIN_PROB_THRESHOLD = 0.55

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
    raw_buffer = BASE_EDGE_BUFFER + DISTANCE_PENALTY * distance

    # --- CAP BUFFER SO IT NEVER EXCEEDS PROBABILITY ---
    buffer = min(raw_buffer, p - 0.05)

    # --- HARD SKIP IF BUFFER KILLS SIGNAL ---
    if p - buffer <= 0:
        return None

    return 1.0 / (p - buffer)


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
                market_total = float(row["best_ou"])
            except Exception:
                continue

            if game_id in seen_games:
                continue
            seen_games.add(game_id)

            # --- NORMAL MODEL PARAMETERS ---
            sigma = sqrt(lam)

            cutoff = market_total
            p_under = normal_cdf(cutoff, lam, sigma)
            p_over = 1.0 - p_under

            side, p = max(
                (("OVER", p_over), ("UNDER", p_under)),
                key=lambda x: x[1]
            )

            if p < MIN_PROB_THRESHOLD:
                continue

            fair_d = fair_decimal(p)
            fair_a = decimal_to_american(fair_d)

            acc_d = acceptable_decimal(p, market_total, lam)
            if acc_d is None:
                continue  # HARD SKIP

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
