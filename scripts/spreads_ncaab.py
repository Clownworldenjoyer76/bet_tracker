#!/usr/bin/env python3
"""
build_edge_ncaab_spreads.py

Mirrors NBA spread workflow exactly, adapted for NCAAB.

Authoritative rules:
- Use projected points to compute margin
- Favorite = higher projected points
- Spread = abs(point_diff), forced to .5
- One output row per team
- Spread sign:
    favorite  -> -spread
    underdog  -> +spread
- Price spreads using COVER probability (NOT win probability)
- Personal juice applied via config/ncaab/ncaab_spreads_juice_table.csv
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

# ============================================================
# HELPERS
# ============================================================

def force_half_point(x: float) -> float:
    """
    Round to nearest 0.5 and force non-integer (.5) spreads.
    Eliminates pushes by construction.
    """
    rounded = round(x * 2) / 2
    if rounded.is_integer():
        return rounded + 0.5
    return rounded


def cover_probability(p_win: float, spread: float) -> float:
    """
    Convert win probability into spread cover probability.
    Conservative, monotonic, and empirically sane.
    """
    s = abs(spread)

    if s <= 1.5:
        adj = 0.015
    elif s <= 3.5:
        adj = 0.035
    elif s <= 5.5:
        adj = 0.060
    elif s <= 7.5:
        adj = 0.085
    elif s <= 10.5:
        adj = 0.11
    else:
        adj = 0.14

    return max(min(p_win - adj, 0.99), 0.01)


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def fair_decimal(p: float) -> float:
    return 1.0 / p


def acceptable_decimal(p: float, juice: float) -> float:
    return 1.0 / max(p - juice, 0.0001)

# ============================================================
# JUICE TABLE HELPERS
# ============================================================

def load_spreads_juice_table(path: Path):
    table = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            table.append({
                "low": float(row["band_low"]),
                "high": float(row["band_high"]),
                "side": row["side"].lower(),  # favorite / underdog / any
                "juice": float(row["extra_juice_pct"]),
            })
    return table


def lookup_spreads_juice(table, spread_abs, side):
    """
    spread_abs : positive float
    side       : 'favorite' or 'underdog'
    """
    for r in table:
        if r["low"] <= spread_abs <= r["high"]:
            if r["side"] == "any" or r["side"] == side:
                return r["juice"]
    return 0.0

# ============================================================
# MAIN
# ============================================================

def main():
    input_files = sorted(INPUT_DIR.glob("edge_ncaab_*.csv"))
    if not input_files:
        raise FileNotFoundError("No NCAAB edge files found")

    latest_file = input_files[-1]
    spreads_juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{today.year}_{today.month:02d}_{today.day:02d}.csv"

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
                p_a = float(a["win_probability"])
                p_b = float(b["win_probability"])
            except (ValueError, TypeError):
                continue

            margin = pts_a - pts_b
            spread = force_half_point(abs(margin))

            # ========================
            # Team A
            # ========================
            side_a = "favorite" if margin > 0 else "underdog"
            spread_a = -spread if side_a == "favorite" else spread

            p_cover_a = cover_probability(p_a, spread)

            juice_a = lookup_spreads_juice(
                spreads_juice_table,
                spread,
                side_a
            )

            fair_d = fair_decimal(p_cover_a)
            acc_d = acceptable_decimal(p_cover_a, juice_a)

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
                "league": "ncaab_spread",
            })

            # ========================
            # Team B
            # ========================
            side_b = "underdog" if side_a == "favorite" else "favorite"
            spread_b = -spread_a

            p_cover_b = cover_probability(p_b, spread)

            juice_b = lookup_spreads_juice(
                spreads_juice_table,
                spread,
                side_b
            )

            fair_d = fair_decimal(p_cover_b)
            acc_d = acceptable_decimal(p_cover_b, juice_b)

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
                "league": "ncaab_spread",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
