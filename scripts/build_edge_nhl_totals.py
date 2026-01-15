#!/usr/bin/env python3
"""
Build NHL Totals Edge File (Single Selection per Game)

Inputs:
- docs/win/clean/win_prob__clean_nhl_*.csv

Outputs:
- docs/win/nhl/edge_nhl_totals_YYYY_MM_DD.csv

Rules:
- Poisson model using total_goals as λ
- EDGE_BUFFER_TOTALS = 7%
- Totals evaluated: 5.5 and 6.5
- Over / Under only
- One output row per game:
    • model_probability >= MIN_PROB
    • closest to 0.50 among qualifying outcomes
"""

import csv
import glob
from math import exp, factorial
from pathlib import Path
from datetime import datetime

EDGE_BUFFER_TOTALS = 0.07
TOTAL_LINES = [5.5, 6.5]
MIN_PROB = 0.55  # selection threshold

INPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR = Path("docs/win/nhl")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def poisson_cdf(k: int, lam: float) -> float:
    return sum((lam ** i) * exp(-lam) / factorial(i) for i in range(k + 1))


def fair_decimal(p: float) -> float:
    return 1.0 / p


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER_TOTALS, 0.0001)


def main():
    input_files = sorted(glob.glob(str(INPUT_DIR / "win_prob__clean_nhl_*.csv")))
    if not input_files:
        raise FileNotFoundError("No clean NHL win probability files found")

    latest_file = input_files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_nhl_totals_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    seen_games = set()

    with open(latest_file, newline="", encoding="utf-8") as infile, \
         open(out_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = [
            "game_id",
            "date",
            "time",
            "team_1",
            "team_2",
            "market_total",
            "side",
            "model_probability",
            "fair_decimal_odds",
            "fair_american_odds",
            "acceptable_decimal_odds",
            "acceptable_american_odds",
            "league"
        ]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            try:
                game_id = row["game_id"]
                lam = float(row["total_goals"])
            except Exception:
                continue

            if game_id in seen_games:
                continue
            seen_games.add(game_id)

            team_1 = row["team"]
            team_2 = row["opponent"]

            candidates = []

            for market_total in TOTAL_LINES:
                cutoff = int(market_total - 0.5)

                p_under = poisson_cdf(cutoff, lam)
                p_over = 1.0 - p_under

                for side, p in (("UNDER", p_under), ("OVER", p_over)):
                    if p < MIN_PROB:
                        continue

                    fair_d = fair_decimal(p)
                    fair_a = decimal_to_american(fair_d)

                    acc_d = acceptable_decimal(p)
                    acc_a = decimal_to_american(acc_d)

                    candidates.append({
                        "game_id": game_id,
                        "date": row["date"],
                        "time": row["time"],
                        "team_1": team_1,
                        "team_2": team_2,
                        "market_total": market_total,
                        "side": side,
                        "model_probability": round(p, 4),
                        "fair_decimal_odds": round(fair_d, 4),
                        "fair_american_odds": fair_a,
                        "acceptable_decimal_odds": round(acc_d, 4),
                        "acceptable_american_odds": acc_a,
                        "league": "nhl"
                    })

            if not candidates:
                continue

            # select outcome closest to 50%
            best = min(
                candidates,
                key=lambda x: abs(x["model_probability"] - 0.5)
            )

            writer.writerow(best)


if __name__ == "__main__":
    main()
