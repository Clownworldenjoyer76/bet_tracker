#!/usr/bin/env python3

import csv
import math
import sys
from pathlib import Path
from collections import defaultdict

# ============================================================
# CONSTANTS
# ============================================================

LEAGUE_STD = 7.2
EPS = 1e-6

EDGE_DIR = Path("docs/win/edge")
SPREADS_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

# ============================================================
# HELPERS
# ============================================================

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

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
        for r in csv.DictReader(f):
            rows.append({
                "low": float(r["band_low"]),
                "high": float(r["band_high"]),
                "side": r["side"].lower(),
                "juice": float(r["extra_juice_pct"]),
            })
    return rows

def lookup_juice(table, spread_abs, side):
    for r in table:
        if r["low"] <= spread_abs <= r["high"]:
            if r["side"] == "any" or r["side"] == side:
                return r["juice"]
    return 0.0

# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: spreads_ncaab.py YYYY_MM_DD")

    date = sys.argv[1]

    edge_file = EDGE_DIR / f"edge_ncaab_{date}.csv"
    spreads_file = SPREADS_DIR / f"norm_dk_ncaab_spreads_{date}.csv"

    if not edge_file.exists():
        raise FileNotFoundError(edge_file)
    if not spreads_file.exists():
        raise FileNotFoundError(spreads_file)

    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    # ----------------------------
    # Load model projections
    # ----------------------------
    edge_by_game = defaultdict(dict)
    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            edge_by_game[r["game_id"]][r["team"]] = r

    # ----------------------------
    # Load DK spreads
    # ----------------------------
    spreads = []
    with spreads_file.open(newline="", encoding="utf-8") as f:
        spreads = list(csv.DictReader(f))

    mm, dd, yy = spreads[0]["date"].split("/")
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_20{yy}_{mm.zfill(2)}_{dd.zfill(2)}.csv"

    fields = [
        "game_id","date","time","team","opponent",
        "spread","spread_probability",
        "fair_decimal_odds","fair_american_odds",
        "acceptable_decimal_odds","acceptable_american_odds",
        "league"
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in spreads:
            team = r["team"]
            opp = r["opponent"]
            spread = float(r["spread"])
            spread_abs = abs(spread)
            side = "favorite" if spread < 0 else "underdog"

            game = None
            for gid, teams in edge_by_game.items():
                if team in teams and opp in teams:
                    game = teams
                    game_id = gid
                    break
            if not game:
                continue

            team_row = game[team]
            opp_row = game[opp]

            team_pts = float(team_row["points"])
            opp_pts = float(opp_row["points"])

            margin = team_pts - opp_pts

            cover_p = clamp(
                normal_cdf((margin + spread) / LEAGUE_STD)
            )

            juice = lookup_juice(juice_table, spread_abs, side)

            fair_dec = 1.0 / cover_p
            acc_dec = 1.0 / max(cover_p - juice, EPS)

            w.writerow({
                "game_id": game_id,
                "date": r["date"],
                "time": r["time"],
                "team": team,
                "opponent": opp,
                "spread": spread,
                "spread_probability": round(cover_p, 6),
                "fair_decimal_odds": round(fair_dec, 6),
                "fair_american_odds": dec_to_amer(fair_dec),
                "acceptable_decimal_odds": round(acc_dec, 6),
                "acceptable_american_odds": dec_to_amer(acc_dec),
                "league": "ncaab_spread",
            })

    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
