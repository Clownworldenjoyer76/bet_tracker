#!/usr/bin/env python3
"""
build_edge_nba_spreads.py

Mirrors NHL spread workflow exactly, adapted for NBA.

Authoritative rules:
- Use projected points to compute margin
- Favorite = higher projected points
- Spread = abs(point_diff), rounded to nearest 0.5
- One output row per team
- Spread sign:
    favorite  -> -spread
    underdog  -> +spread
- Price spreads using model win probability
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from math import copysign

# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# PARAMETERS (MATCH NHL)
# ============================================================

EDGE_BUFFER = 0.05   # same buffer concept as NHL

# ============================================================
# HELPERS
# ============================================================

def round_to_half(x: float) -> float:
    return round(x * 2) / 2


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def fair_decimal(p: float) -> float:
    return 1.0 / p


def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER, 0.0001)


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

    with open(latest_file, newline="", encoding="utf-8") as f:
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

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for game_id, rows in games.items():
            if len(rows) != 2:
                continue

            a, b = rows

            try:
                pts_a = float(a["points"])
                pts_b = float(b["points"])
                p_a = float(a["win_probability"])
                p_b = float(b["win_probability"])
            except (ValueError, TypeError):
                continue

            margin = pts_a - pts_b
            spread = round_to_half(abs(margin))

            # team A
            spread_a = -spread if margin > 0 else spread
            p_sel_a = p_a

            fair_d = fair_decimal(p_sel_a)
            acc_d = acceptable_decimal(p_sel_a)

            writer.writerow({
                "game_id": game_id,
                "date": a["date"],
                "time": a["time"],
                "team": a["team"],
                "opponent": a["opponent"],
                "spread": spread_a,
                "model_probability": round(p_sel_a, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

            # team B
            spread_b = -spread_a
            p_sel_b = p_b

            fair_d = fair_decimal(p_sel_b)
            acc_d = acceptable_decimal(p_sel_b)

            writer.writerow({
                "game_id": game_id,
                "date": b["date"],
                "time": b["time"],
                "team": b["team"],
                "opponent": b["opponent"],
                "spread": spread_b,
                "model_probability": round(p_sel_b, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
