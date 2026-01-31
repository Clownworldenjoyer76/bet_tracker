#!/usr/bin/env python3
"""
build_edge_ncaab_spreads.py

Market-anchored NCAAB spread pricing using DK spreads.

Rules:
- Spread comes from DK normalized file
- Historical sigma = 7.2
- Cover probability = NormalCDF(spread / sigma)
- One output row per team
- Favorite spread negative, underdog positive
- Juice applied via config/ncaab/ncaab_spreads_juice_table.csv
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
SPREADS_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

# ============================================================
# CONSTANTS
# ============================================================

LEAGUE_STD = 7.2
EPS = 1e-6

# ============================================================
# HELPERS
# ============================================================

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

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
# JUICE TABLE
# ============================================================

def load_spreads_juice_table(path: Path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "low": float(r["band_low"]),
                "high": float(r["band_high"]),
                "side": r["side"].lower(),
                "juice": float(r["extra_juice_pct"]),
            })
    return rows

def lookup_spreads_juice(table, spread_abs, side):
    for r in table:
        if r["low"] <= spread_abs <= r["high"]:
            if r["side"] in ("any", side):
                return r["juice"]
    return 0.0

# ============================================================
# MAIN
# ============================================================

def main():
    edge_file = sorted(EDGE_DIR.glob("edge_ncaab_*.csv"))[-1]
    spreads_file = sorted(SPREADS_DIR.glob("norm_dk_ncaab_spreads_*.csv"))[-1]

    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    edge_by_game = defaultdict(list)
    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            edge_by_game[r["game_id"]].append(r)

    spread_by_team = {}
    with spreads_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            spread_by_team[r["team"]] = float(r["spread"])

    sample_row = next(iter(edge_by_game.values()))[0]
    dt = datetime.strptime(sample_row["date"], "%m/%d/%Y")
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{dt.year}_{dt.month:02d}_{dt.day:02d}.csv"

    fields = [
        "game_id","date","time","team","opponent",
        "spread","model_probability",
        "fair_decimal_odds","fair_american_odds",
        "acceptable_decimal_odds","acceptable_american_odds",
        "league"
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for gid, rows in edge_by_game.items():
            if len(rows) != 2:
                continue

            a, b = rows
            ta, tb = a["team"], b["team"]

            if ta not in spread_by_team or tb not in spread_by_team:
                continue

            sa = spread_by_team[ta]
            sb = spread_by_team[tb]

            # Identify favorite
            if sa < sb:
                fav, dog = (a, sa), (b, sb)
            else:
                fav, dog = (b, sb), (a, sa)

            spread_abs = abs(fav[1])

            # Market-implied cover probability
            p_fav = clamp(normal_cdf(spread_abs / LEAGUE_STD))
            p_dog = 1.0 - p_fav

            for row, spread, p, side in [
                (fav[0], -spread_abs, p_fav, "favorite"),
                (dog[0],  spread_abs, p_dog, "underdog"),
            ]:
                juice = lookup_spreads_juice(juice_table, spread_abs, side)

                fair_d = fair_decimal(p)
                acc_d = acceptable_decimal(p, juice)

                w.writerow({
                    "game_id": gid,
                    "date": row["date"],
                    "time": row["time"],
                    "team": row["team"],
                    "opponent": row["opponent"],
                    "spread": spread,
                    "model_probability": round(p, 6),
                    "fair_decimal_odds": round(fair_d, 6),
                    "fair_american_odds": decimal_to_american(fair_d),
                    "acceptable_decimal_odds": round(acc_d, 6),
                    "acceptable_american_odds": decimal_to_american(acc_d),
                    "league": "ncaab_spread",
                })

    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
