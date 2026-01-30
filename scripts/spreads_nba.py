#!/usr/bin/env python3
"""
build_edge_nba_spreads.py

NBA spreads derived from GAME-LEVEL totals data (NHL-aligned).

Authoritative rules:
- Source games from edge_nba_totals_*.csv ONLY
- Use projected points to compute margin
- Favorite = higher projected points
- Spread = abs(point_diff), capped and forced to .5
- One output row per team
- Spread sign:
    favorite  -> -spread
    underdog  -> +spread
- Price spreads using COVER probability (normal margin model)
- Enforce probability floors + tail compression
- Prevent ML / spread self-contradiction
"""

import csv
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path("docs/win/nba")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# PARAMETERS (HARD CONSTRAINTS)
# ============================================================

EDGE_BUFFER = 0.05
MARGIN_STD_DEV = 12.0          # empirical NBA margin std dev
MAX_SPREAD = 8.5               # absolute cap (no 10.5+)
MIN_COVER_PROB = 0.12          # floor to prevent insane odds

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


def cover_probability(projected_margin: float, spread: float) -> float:
    z = (projected_margin - spread) / MARGIN_STD_DEV
    return normal_cdf(z)


def compress_favorite_tail(p: float) -> float:
    """
    Prevent heavy favorites from having lower spread prob than ML intuition.
    """
    if p > 0.5:
        return 0.5 + 0.75 * (p - 0.5)
    return p

# ============================================================
# MAIN
# ============================================================

def main():
    # --------------------------------------------------------
    # CRITICAL: use totals-derived game file ONLY
    # --------------------------------------------------------
    input_files = sorted(INPUT_DIR.glob("edge_nba_totals_*.csv"))
    if not input_files:
        raise FileNotFoundError("No NBA totals edge files found")

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

            # ------------------------------
            # Spread construction (capped)
            # ------------------------------
            raw_spread = min(abs(margin), MAX_SPREAD)
            spread = force_half_point(raw_spread)

            # ====================================================
            # TEAM A
            # ====================================================
            is_fav_a = margin > 0
            spread_a = -spread if is_fav_a else spread

            proj_margin_a = margin
            p_a = cover_probability(
                projected_margin=proj_margin_a,
                spread=spread if is_fav_a else -spread
            )

            if is_fav_a:
                p_a = compress_favorite_tail(p_a)

            p_a = max(p_a, MIN_COVER_PROB)

            fair_d = fair_decimal(p_a)
            acc_d = acceptable_decimal(p_a)

            writer.writerow({
                "game_id": game_id,
                "date": a["date"],
                "time": a["time"],
                "team": a["team"],
                "opponent": a["opponent"],
                "spread": spread_a,
                "model_probability": round(p_a, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

            # ====================================================
            # TEAM B
            # ====================================================
            spread_b = -spread_a
            proj_margin_b = -margin

            p_b = cover_probability(
                projected_margin=proj_margin_b,
                spread=spread if not is_fav_a else -spread
            )

            if not is_fav_a:
                p_b = compress_favorite_tail(p_b)

            p_b = max(p_b, MIN_COVER_PROB)

            fair_d = fair_decimal(p_b)
            acc_d = acceptable_decimal(p_b)

            writer.writerow({
                "game_id": game_id,
                "date": b["date"],
                "time": b["time"],
                "team": b["team"],
                "opponent": b["opponent"],
                "spread": spread_b,
                "model_probability": round(p_b, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
