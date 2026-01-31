#!/usr/bin/env python3
"""
build_edge_ncaab_spreads.py

Option A: Mirror NBA pricing logic while still using DK spreads.

Rules enforced:
- Spread comes from DK normalized file (norm_dk_ncaab_spreads_*.csv)
- Cover probabilities come from projected margin + normal CDF (like NBA)
- One output row per team
- Spread sign preserved from DK
- Personal juice applied via config/ncaab/ncaab_spreads_juice_table.csv
"""

import csv
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ============================================================
# PATHS
# ============================================================

EDGE_DIR = Path("docs/win/edge")
DK_SPREADS_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

# ============================================================
# CONSTANTS (added)
# ============================================================
# Tune this if you have a league-specific calibration.
# Larger -> probabilities closer to 50/50 for the same spread/margin.
LEAGUE_STD = 10.5
EPS = 1e-6

# ============================================================
# HELPERS
# ============================================================

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def clamp(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

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
    for r in table:
        if r["low"] <= spread_abs <= r["high"]:
            if r["side"] == "any" or r["side"] == side:
                return r["juice"]
    return 0.0

# ============================================================
# MAIN
# ============================================================

def main():
    edge_files = sorted(EDGE_DIR.glob("edge_ncaab_*.csv"))
    dk_spread_files = sorted(DK_SPREADS_DIR.glob("norm_dk_ncaab_spreads_*.csv"))

    if not edge_files:
        raise FileNotFoundError("No NCAAB edge files found")
    if not dk_spread_files:
        raise FileNotFoundError("No DK NCAAB spread files found")

    edge_file = edge_files[-1]
    dk_spreads_file = dk_spread_files[-1]
    spreads_juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    # ------------------------
    # Load DK spreads
    # ------------------------
    spread_by_team = {}
    with dk_spreads_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            spread_by_team[r["team"]] = float(r["spread"])

    # ------------------------
    # Load edge data
    # ------------------------
    games = defaultdict(list)
    slate_date = None

    with edge_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not slate_date and row.get("date"):
                slate_date = row["date"]
            if row.get("game_id"):
                games[row["game_id"]].append(row)

    if not slate_date:
        raise ValueError("Could not determine slate date from input file")

    dt = datetime.strptime(slate_date, "%m/%d/%Y")
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{dt.year}_{dt.month:02d}_{dt.day:02d}.csv"

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

            if a["team"] not in spread_by_team or b["team"] not in spread_by_team:
                continue

            try:
                pts_a = float(a["points"])
                pts_b = float(b["points"])
            except (ValueError, TypeError):
                continue

            spread_a = float(spread_by_team[a["team"]])
            spread_b = float(spread_by_team[b["team"]])

            # Infer sides from DK spread sign
            side_a = "favorite" if spread_a < 0 else "underdog"
            side_b = "favorite" if spread_b < 0 else "underdog"
            abs_spread = abs(spread_a)

            # Projected margin from model points (team - opponent)
            margin_a = pts_a - pts_b
            margin_b = -margin_a

            # Cover probabilities via normal CDF (NBA-style)
            p_cover_a = clamp(normal_cdf((margin_a + spread_a) / LEAGUE_STD))
            p_cover_b = clamp(normal_cdf((margin_b + spread_b) / LEAGUE_STD))

            # Apply juice table per side/band
            juice_a = lookup_spreads_juice(spreads_juice_table, abs_spread, side_a)
            juice_b = lookup_spreads_juice(spreads_juice_table, abs_spread, side_b)

            fair_a = fair_decimal(p_cover_a)
            acc_a = acceptable_decimal(p_cover_a, juice_a)

            fair_b = fair_decimal(p_cover_b)
            acc_b = acceptable_decimal(p_cover_b, juice_b)

            writer.writerow({
                "game_id": game_id,
                "date": a["date"],
                "time": a["time"],
                "team": a["team"],
                "opponent": a["opponent"],
                "spread": spread_a,
                "model_probability": round(p_cover_a, 6),
                "fair_decimal_odds": round(fair_a, 6),
                "fair_american_odds": decimal_to_american(fair_a),
                "acceptable_decimal_odds": round(acc_a, 6),
                "acceptable_american_odds": decimal_to_american(acc_a),
                "league": "ncaab_spread",
            })

            writer.writerow({
                "game_id": game_id,
                "date": b["date"],
                "time": b["time"],
                "team": b["team"],
                "opponent": b["opponent"],
                "spread": spread_b,
                "model_probability": round(p_cover_b, 6),
                "fair_decimal_odds": round(fair_b, 6),
                "fair_american_odds": decimal_to_american(fair_b),
                "acceptable_decimal_odds": round(acc_b, 6),
                "acceptable_american_odds": decimal_to_american(acc_b),
                "league": "ncaab_spread",
            })

    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
