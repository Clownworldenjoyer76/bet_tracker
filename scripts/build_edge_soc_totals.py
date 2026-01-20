#!/usr/bin/env python3
"""
Build Soccer Totals Edge File (Market-Anchored)

Contract:
- Use best_ou as the ONLY total line
- Decide OVER / UNDER / NO PLAY
- No alternate totals
"""

import csv
import glob
from math import exp, factorial
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# -----------------------------
# PARAMETERS (EXPLICIT)
# -----------------------------
EDGE_BUFFER_TOTALS = 0.035

MIN_EDGE = 0.055          # minimum absolute edge between sides
MIN_SIDE_PROB = 0.54      # minimum probability to take a side
MIN_LAM = 1.1             # sanity bounds
MAX_LAM = 4.2

HOME_MULT = 1.10
AWAY_MULT = 0.90

INPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR = Path("docs/win/soc")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# MATH HELPERS
# -----------------------------
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


# -----------------------------
# MAIN
# -----------------------------
def main():
    input_files = sorted(
        glob.glob(str(INPUT_DIR / "win_prob__clean_soc_*.csv"))
    )
    if not input_files:
        raise FileNotFoundError("No clean soccer win probability files found")

    latest_file = input_files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_soc_totals_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    games = defaultdict(list)

    with open(latest_file, newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            if not row.get("game_id"):
                continue
            if not row.get("goals"):
                continue
            if not row.get("best_ou"):
                continue
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
            # strict invariant: exactly two rows per match
            if len(rows) != 2:
                continue

            try:
                # rows[0] = away, rows[1] = home
                lam_total = (
                    float(rows[0]["goals"]) * AWAY_MULT +
                    float(rows[1]["goals"]) * HOME_MULT
                )
            except ValueError:
                continue

            # sanity bounds
            if not (MIN_LAM <= lam_total <= MAX_LAM):
                continue

            try:
                market_total = float(rows[0]["best_ou"])
            except ValueError:
                continue

            cutoff = int(market_total - 0.5)

            p_under = poisson_cdf(cutoff, lam_total)
            p_over = 1.0 - p_under

            edge = abs(p_over - p_under)

            # enforce edge threshold
            if edge < MIN_EDGE:
                continue

            # side selection
            if p_over >= MIN_SIDE_PROB and p_over > p_under:
                side = "OVER"
                p = p_over
            elif p_under >= MIN_SIDE_PROB and p_under > p_over:
                side = "UNDER"
                p = p_under
            else:
                continue

            fair_d = fair_decimal(p)
            fair_a = decimal_to_american(fair_d)
            acc_d = acceptable_decimal(p)
            acc_a = decimal_to_american(acc_d)

            writer.writerow({
                "game_id": game_id,
                "date": rows[0]["date"],
                "time": rows[0]["time"],
                "team_1": rows[0]["team"],
                "team_2": rows[1]["team"],
                "market_total": market_total,
                "side": side,
                "model_probability": round(p, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": fair_a,
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": acc_a,
                "league": "soc_ou",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
