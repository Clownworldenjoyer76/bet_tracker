#!/usr/bin/env python3
"""
build_edge_ncaab_spreads.py

NCAAB spread pricing with market–model blend (Option C).

Rules enforced:
- Spread comes from DK normalized file
- Cover probability computed ONCE per game (favorite)
- Underdog probability = 1 - favorite probability
- Effective margin = 50% model margin + 50% market spread
- Normal CDF with historical sigma = 7.2
- One output row per team
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
# CONSTANTS
# ============================================================

LEAGUE_STD = 7.2
EPS = 1e-6
MODEL_WEIGHT = 0.5
MARKET_WEIGHT = 0.5

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
    return 1.0 / max(p - juice, EPS)

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
        raise ValueError("Could not determine slate date")

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

            r1, r2 = rows

            if r1["team"] not in spread_by_team or r2["team"] not in spread_by_team:
                continue

            try:
                pts_1 = float(r1["points"])
                pts_2 = float(r2["points"])
            except (ValueError, TypeError):
                continue

            spread_1 = spread_by_team[r1["team"]]
            spread_2 = spread_by_team[r2["team"]]

            # Identify favorite
            if spread_1 < 0:
                fav, dog = r1, r2
                fav_pts, dog_pts = pts_1, pts_2
                fav_spread, dog_spread = spread_1, spread_2
            else:
                fav, dog = r2, r1
                fav_pts, dog_pts = pts_2, pts_1
                fav_spread, dog_spread = spread_2, spread_1

            model_margin = fav_pts - dog_pts
            s = abs(fav_spread)

            effective_margin = (
                MODEL_WEIGHT * model_margin +
                MARKET_WEIGHT * s
            )

            p_fav = clamp(normal_cdf((effective_margin - s) / LEAGUE_STD))
            p_dog = 1.0 - p_fav

            juice_fav = lookup_spreads_juice(spreads_juice_table, s, "favorite")
            juice_dog = lookup_spreads_juice(spreads_juice_table, s, "underdog")

            fair_fav = fair_decimal(p_fav)
            fair_dog = fair_decimal(p_dog)

            acc_fav = acceptable_decimal(p_fav, juice_fav)
            acc_dog = acceptable_decimal(p_dog, juice_dog)

            writer.writerow({
                "game_id": game_id,
                "date": fav["date"],
                "time": fav["time"],
                "team": fav["team"],
                "opponent": fav["opponent"],
                "spread": fav_spread,
                "model_probability": round(p_fav, 6),
                "fair_decimal_odds": round(fair_fav, 6),
                "fair_american_odds": decimal_to_american(fair_fav),
                "acceptable_decimal_odds": round(acc_fav, 6),
                "acceptable_american_odds": decimal_to_american(acc_fav),
                "league": "ncaab_spread",
            })

            writer.writerow({
                "game_id": game_id,
                "date": dog["date"],
                "time": dog["time"],
                "team": dog["team"],
                "opponent": dog["opponent"],
                "spread": dog_spread,
                "model_probability": round(p_dog, 6),
                "fair_decimal_odds": round(fair_dog, 6),
                "fair_american_odds": decimal_to_american(fair_dog),
                "acceptable_decimal_odds": round(acc_dog, 6),
                "acceptable_american_odds": decimal_to_american(acc_dog),
                "league": "ncaab_spread",
            })

    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
