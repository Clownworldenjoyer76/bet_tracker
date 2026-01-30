#!/usr/bin/env python3
"""
build_edge_nba_spreads.py

Authoritative NBA spread builder.

Rules:
- Use FINAL nba file (same source as ML)
- Spread from projected points
- Probabilities derived from win_probability (consistency guarantee)
- Force .5 spreads (no pushes)
- One row per team
"""

import csv
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ============================================================
# PATHS
# ============================================================

FINAL_DIR = Path("docs/win/final")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EDGE_BUFFER = 0.05
MARGIN_STD_DEV = 12.0  # NBA empirical

# ============================================================
# HELPERS
# ============================================================

def force_half_point(x: float) -> float:
    x = abs(x)
    rounded = round(x * 2) / 2
    if rounded.is_integer():
        return rounded + 0.5
    return rounded

def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def cover_prob_from_win_prob(win_p: float, margin: float) -> float:
    """
    Convert win probability into spread cover probability.
    Keeps markets internally consistent.
    """
    z = margin / MARGIN_STD_DEV
    adj = normal_cdf(z)
    return max(min(win_p * adj, 0.95), 0.05)

def dec_to_amer(d: float) -> int:
    if d >= 2:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))

def fair_decimal(p: float) -> float:
    return 1.0 / max(p, 0.0001)

def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER, 0.0001)

# ============================================================
# MAIN
# ============================================================

def main():
    final_files = sorted(FINAL_DIR.glob("final_nba_*.csv"))
    if not final_files:
        raise FileNotFoundError("No final NBA files found")

    latest = final_files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_nba_spreads_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    games = defaultdict(list)

    with latest.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
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

        for gid, rows in games.items():
            if len(rows) != 2:
                continue

            a, b = rows

            pts_a = float(a["points"])
            pts_b = float(b["points"])
            p_a = float(a["win_probability"])
            p_b = float(b["win_probability"])

            margin = pts_a - pts_b
            spread = force_half_point(margin)

            # ---------- Team A ----------
            spread_a = -spread if margin > 0 else spread
            p_cover_a = cover_prob_from_win_prob(p_a, margin)

            fair_d = fair_decimal(p_cover_a)
            acc_d = acceptable_decimal(p_cover_a)

            writer.writerow({
                "game_id": gid,
                "date": a["date"],
                "time": a["time"],
                "team": a["team"],
                "opponent": a["opponent"],
                "spread": spread_a,
                "model_probability": round(p_cover_a, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": dec_to_amer(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": dec_to_amer(acc_d),
                "league": "nba_spread",
            })

            # ---------- Team B ----------
            spread_b = -spread_a
            p_cover_b = cover_prob_from_win_prob(p_b, -margin)

            fair_d = fair_decimal(p_cover_b)
            acc_d = acceptable_decimal(p_cover_b)

            writer.writerow({
                "game_id": gid,
                "date": b["date"],
                "time": b["time"],
                "team": b["team"],
                "opponent": b["opponent"],
                "spread": spread_b,
                "model_probability": round(p_cover_b, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": dec_to_amer(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": dec_to_amer(acc_d),
                "league": "nba_spread",
            })

    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
