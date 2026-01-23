#!/usr/bin/env python3
"""
Build NCAAB Totals Evaluation File (Model-Anchored)

Rules:
- No live market odds assumed
- Use best_ou as the comparison total
- OVER if model total (λ) > best_ou
- UNDER if model total (λ) < best_ou
- NO PLAY if best_ou missing/invalid or totals equal
- Normal model with μ = total_points
- σ = sqrt(μ)
- Price every valid game
"""

import csv
import glob
from math import sqrt, erf
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# -----------------------------
# PARAMETERS
# -----------------------------
EDGE_BUFFER_TOTALS = 0.07

MIN_LAM = 100.0
MAX_LAM = 200.0

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/ncaab")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# MATH HELPERS
# -----------------------------
def normal_cdf(x: float, mu: float, sigma: float) -> float:
    z = (x - mu) / (sigma * sqrt(2))
    return 0.5 * (1 + erf(z))


def fair_decimal(p: float) -> float:
    return 1.0 / p


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER_TOTALS, 0.0001)

# -----------------------------
# MAIN
# -----------------------------
def main():
    input_files = sorted(glob.glob(str(INPUT_DIR / "edge_ncaab_*.csv")))
    if not input_files:
        raise FileNotFoundError("No NCAAB edge files found")

    latest_file = input_files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_ncaab_totals_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    games = defaultdict(list)

    with open(latest_file, newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            if row.get("game_id"):
                games[row["game_id"]].append(row)

    with open(out_path, "w", newline="", encoding="utf-8") as outfile:
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
            "league",
        ]

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for game_id, rows in games.items():

            if not rows:
                continue

            row = rows[0]

            team_1 = row.get("team", "")
            team_2 = row.get("opponent", "")
            date = row.get("date", "")
            time = row.get("time", "")

            side = "NO PLAY"
            p_selected = None

            try:
                lam = float(row["total_points"])
            except (ValueError, TypeError):
                lam = None

            try:
                market_total = float(row.get("best_ou", ""))
            except (ValueError, TypeError):
                market_total = ""

            if (
                lam is not None
                and market_total != ""
                and MIN_LAM <= lam <= MAX_LAM
            ):
                sigma = sqrt(lam)

                # continuity correction
                p_under = normal_cdf(market_total, lam, sigma)
                p_over = 1.0 - p_under

                if lam > market_total:
                    side = "OVER"
                    p_selected = p_over
                elif lam < market_total:
                    side = "UNDER"
                    p_selected = p_under

            if p_selected is not None:
                fair_d = fair_decimal(p_selected)
                fair_a = decimal_to_american(fair_d)
                acc_d = acceptable_decimal(p_selected)
                acc_a = decimal_to_american(acc_d)

                writer.writerow({
                    "game_id": game_id,
                    "date": date,
                    "time": time,
                    "team_1": team_1,
                    "team_2": team_2,
                    "market_total": market_total,
                    "side": side,
                    "model_probability": round(p_selected, 4),
                    "fair_decimal_odds": round(fair_d, 4),
                    "fair_american_odds": fair_a,
                    "acceptable_decimal_odds": round(acc_d, 4),
                    "acceptable_american_odds": acc_a,
                    "league": "ncaab_ou",
                })
            else:
                writer.writerow({
                    "game_id": game_id,
                    "date": date,
                    "time": time,
                    "team_1": team_1,
                    "team_2": team_2,
                    "market_total": market_total,
                    "side": "NO PLAY",
                    "model_probability": "",
                    "fair_decimal_odds": "",
                    "fair_american_odds": "",
                    "acceptable_decimal_odds": "",
                    "acceptable_american_odds": "",
                    "league": "ncaab_ou",
                })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
