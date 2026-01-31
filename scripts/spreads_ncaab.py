#!/usr/bin/env python3

import csv
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ============================================================
# CONSTANTS
# ============================================================

LEAGUE_STD = 7.2
MODEL_WEIGHT = 0.15
MARKET_WEIGHT = 0.85
EPS = 1e-6

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# MATH HELPERS
# ============================================================

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def clamp(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

# ============================================================
# JUICE TABLE
# ============================================================

def load_spreads_juice_table(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "low": float(r["band_low"]),
                "high": float(r["band_high"]),
                "side": r["side"].lower(),  # favorite / underdog / any
                "extra": float(r["extra_juice_pct"]),
            })
    return rows

def lookup_juice_multiplier(table, spread_abs: float, side: str) -> float:
    for r in table:
        if r["low"] <= spread_abs <= r["high"]:
            if r["side"] == "any" or r["side"] == side:
                return 1.0 + r["extra"]
    return 1.0

# ============================================================
# COVER PROBABILITY
# ============================================================

def cover_probability(model_margin: float, market_spread: float) -> float:
    """
    model_margin   = proj_pts_fav - proj_pts_dog
    market_spread  = DK spread for team (negative if favorite)
    """
    effective_margin = (
        MODEL_WEIGHT * model_margin +
        MARKET_WEIGHT * (-market_spread)
    )

    z = (effective_margin + market_spread) / LEAGUE_STD
    return clamp(normal_cdf(z))

# ============================================================
# MAIN
# ============================================================

def main():
    input_files = sorted(INPUT_DIR.glob("edge_ncaab_*.csv"))
    if not input_files:
        raise FileNotFoundError("No NCAAB edge files found")

    latest = input_files[-1]
    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    games = defaultdict(list)
    slate_date = None

    with latest.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not slate_date:
                slate_date = r["date"]
            games[r["game_id"]].append(r)

    dt = datetime.strptime(slate_date, "%m/%d/%Y")
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{dt.year}_{dt.month:02d}_{dt.day:02d}.csv"

    fields = [
        "game_id","date","time","team","opponent","spread",
        "model_probability",
        "fair_decimal_odds","fair_american_odds",
        "acceptable_decimal_odds","acceptable_american_odds",
        "league"
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for gid, rows in games.items():
            if len(rows) != 2:
                continue

            a, b = rows

            pts_a = float(a["points"])
            pts_b = float(b["points"])

            margin = pts_a - pts_b
            spread_abs = abs(float(a["spread"]))

            # Team A
            side_a = "favorite" if float(a["spread"]) < 0 else "underdog"
            p_a = cover_probability(margin, float(a["spread"]))

            mult_a = lookup_juice_multiplier(juice_table, spread_abs, side_a)

            fair_a = 1.0 / p_a
            acc_a = 1.0 / clamp(p_a * mult_a)

            w.writerow({
                "game_id": gid,
                "date": a["date"],
                "time": a["time"],
                "team": a["team"],
                "opponent": a["opponent"],
                "spread": float(a["spread"]),
                "model_probability": round(p_a, 6),
                "fair_decimal_odds": round(fair_a, 6),
                "fair_american_odds": dec_to_amer(fair_a),
                "acceptable_decimal_odds": round(acc_a, 6),
                "acceptable_american_odds": dec_to_amer(acc_a),
                "league": "ncaab_spread",
            })

            # Team B (complement)
            side_b = "underdog" if side_a == "favorite" else "favorite"
            p_b = clamp(1.0 - p_a)

            mult_b = lookup_juice_multiplier(juice_table, spread_abs, side_b)

            fair_b = 1.0 / p_b
            acc_b = 1.0 / clamp(p_b * mult_b)

            w.writerow({
                "game_id": gid,
                "date": b["date"],
                "time": b["time"],
                "team": b["team"],
                "opponent": b["opponent"],
                "spread": -float(a["spread"]),
                "model_probability": round(p_b, 6),
                "fair_decimal_odds": round(fair_b, 6),
                "fair_american_odds": dec_to_amer(fair_b),
                "acceptable_decimal_odds": round(acc_b, 6),
                "acceptable_american_odds": dec_to_amer(acc_b),
                "league": "ncaab_spread",
            })

    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
