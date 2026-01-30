#!/usr/bin/env python3
"""
build_edge_nba_spreads.py

NBA spreads derived from the SAME game-level belief as moneyline.
No contradictions, no probability leakage.

Rules:
- Use projected points to compute margin
- Spread = abs(point_diff), forced to .5 (no pushes)
- ONE cover probability per game (favorite)
- Underdog prob = 1 - favorite prob
- No win_prob multiplication
"""

import csv
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# PARAMETERS
# ============================================================

EDGE_BUFFER = 0.05
MARGIN_STD_DEV = 12.0  # empirical NBA margin std dev

# ============================================================
# HELPERS
# ============================================================

def force_half_point(x: float) -> float:
    rounded = round(x * 2) / 2
    return rounded + 0.5 if rounded.is_integer() else rounded


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def fair_decimal(p: float) -> float:
    return 1.0 / max(p, 1e-6)


def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER, 1e-6)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def favorite_cover_probability(projected_margin: float, spread: float) -> float:
    z = (projected_margin - spread) / MARGIN_STD_DEV
    return normal_cdf(z)

# ============================================================
# MAIN
# ============================================================

def main():
    input_files = sorted(INPUT_DIR.glob("edge_nba_*.csv"))
    if not input_files:
        raise FileNotFoundError("No NBA edge files found")

    latest_file = input_files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_nba_spreads_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    games = defaultdict(list)

    with latest_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("game_id"):
                games[row["game_id"]].append(row)

    fieldnames = [
        "game_id",
        "date",
        "time",
        "team",
        "opponent",
        "spread",
        "model_probability",
        "fair_decimal_odds",
        "fair_american_odds",
        "acceptable_decimal_odds",
        "acceptable_american_odds",
        "league",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for game_id, rows in games.items():
            if len(rows) != 2:
                continue

            a, b = rows

            try:
                pts_a = float(a["points"])
                pts_b = float(b["points"])
            except (ValueError, TypeError):
                continue

            margin = pts_a - pts_b
            spread = force_half_point(abs(margin))

            # Determine favorite
            if margin > 0:
                fav, dog = a, b
                fav_margin = margin
                fav_spread = -spread
                dog_spread = spread
            else:
                fav, dog = b, a
                fav_margin = -margin
                fav_spread = -spread
                dog_spread = spread

            # ONE probability
            p_fav_cover = favorite_cover_probability(fav_margin, spread)
            p_dog_cover = 1.0 - p_fav_cover

            # ---- Favorite row ----
            fair_d = fair_decimal(p_fav_cover)
            acc_d = acceptable_decimal(p_fav_cover)

            writer.writerow({
                "game_id": game_id,
                "date": fav["date"],
                "time": fav["time"],
                "team": fav["team"],
                "opponent": fav["opponent"],
                "spread": fav_spread,
                "model_probability": round(p_fav_cover, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

            # ---- Underdog row ----
            fair_d = fair_decimal(p_dog_cover)
            acc_d = acceptable_decimal(p_dog_cover)

            writer.writerow({
                "game_id": game_id,
                "date": dog["date"],
                "time": dog["time"],
                "team": dog["team"],
                "opponent": dog["opponent"],
                "spread": dog_spread,
                "model_probability": round(p_dog_cover, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
