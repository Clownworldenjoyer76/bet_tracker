#!/usr/bin/env python3
"""
build_edge_nba_spreads.py

NBA spreads derived DIRECTLY from moneyline probability.
No projected-points pricing. No contradictions.

Authoritative rules:
- Moneyline probability is the source of truth
- Expected margin derived from ML probability
- Spread derived from expected margin (forced .5)
- Cover probability derived from same distribution
- One row per team (mirrors existing format)
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
# PARAMETERS (NBA)
# ============================================================

EDGE_BUFFER = 0.05
MARGIN_SCALE = 6.5        # controls how ML → margin
MARGIN_STD_DEV = 12.0     # NBA scoring margin σ

# ============================================================
# HELPERS
# ============================================================

def force_half_point(x: float) -> float:
    rounded = round(x * 2) / 2
    if rounded.is_integer():
        return rounded + 0.5
    return rounded


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def fair_decimal(p: float) -> float:
    return 1.0 / max(p, 0.0001)


def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER, 0.0001)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def expected_margin_from_ml(p: float) -> float:
    """
    Convert win probability → expected scoring margin.
    """
    p = min(max(p, 0.001), 0.999)
    return MARGIN_SCALE * math.log(p / (1.0 - p))


def cover_probability(expected_margin: float, spread: float) -> float:
    """
    P(team covers given expected margin and market spread)
    """
    z = (expected_margin - spread) / MARGIN_STD_DEV
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
                p_a = float(a["win_probability"])
                p_b = float(b["win_probability"])
            except (ValueError, TypeError):
                continue

            # Expected margins from ML
            exp_margin_a = expected_margin_from_ml(p_a)
            exp_margin_b = -exp_margin_a

            spread = force_half_point(abs(exp_margin_a))

            # ---------------- Team A ----------------
            spread_a = -spread if exp_margin_a > 0 else spread
            p_cover_a = cover_probability(exp_margin_a, spread)

            fair_d = fair_decimal(p_cover_a)
            acc_d = acceptable_decimal(p_cover_a)

            writer.writerow({
                "game_id": game_id,
                "date": a["date"],
                "time": a["time"],
                "team": a["team"],
                "opponent": a["opponent"],
                "spread": spread_a,
                "model_probability": round(p_cover_a, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

            # ---------------- Team B ----------------
            spread_b = -spread_a
            p_cover_b = cover_probability(exp_margin_b, spread)

            fair_d = fair_decimal(p_cover_b)
            acc_d = acceptable_decimal(p_cover_b)

            writer.writerow({
                "game_id": game_id,
                "date": b["date"],
                "time": b["time"],
                "team": b["team"],
                "opponent": b["opponent"],
                "spread": spread_b,
                "model_probability": round(p_cover_b, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
