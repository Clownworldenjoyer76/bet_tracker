#!/usr/bin/env python3

import csv
import math
from pathlib import Path

# ================= PATHS =================

TOTALS_DIR = Path("docs/win/nba")
EDGE_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ================= CONSTANTS =================

LEAGUE_MARGIN_STD = 7.2
JUICE = 1.047619

# ================= HELPERS =================

def round_half(x: float) -> float:
    return round(x * 2) / 2

def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def dec_to_amer(d: float) -> int:
    if d >= 2:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))

# ================= MAIN =================

def main():
    totals_path = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))[-1]
    with totals_path.open(newline="", encoding="utf-8") as f:
        totals = list(csv.DictReader(f))

    m, d, y = totals[0]["date"].split("/")
    out_path = OUTPUT_DIR / f"edge_nba_spreads_{y}_{m}_{d}.csv"

    edge_path = sorted(EDGE_DIR.glob("edge_nba_*.csv"))[-1]
    edge_by_game = {}
    with edge_path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            edge_by_game.setdefault(r["game_id"], []).append(r)

    fields = [
        "game_id","date","time","away_team","home_team",
        "away_team_proj_pts","home_team_proj_pts",
        "away_spread","home_spread",
        "away_ml_prob","home_ml_prob",
        "away_spread_probability","home_spread_probability",
        "fair_away_spread_decimal_odds","fair_away_spread_american_odds",
        "fair_home_spread_decimal_odds","fair_home_spread_american_odds",
        "acceptable_away_spread_decimal_odds","acceptable_away_spread_american_odds",
        "acceptable_home_spread_decimal_odds","acceptable_home_spread_american_odds",
        "league"
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in totals:
            gid = r["game_id"]
            away, home = r["team_1"], r["team_2"]
            rows = edge_by_game.get(gid)
            if not rows or len(rows) != 2:
                continue

            if rows[0]["team"] == away:
                a, h = rows
            else:
                h, a = rows

            away_pts = float(a["points"])
            home_pts = float(h["points"])
            margin = home_pts - away_pts

            home_spread = round_half(margin)
            away_spread = -home_spread

            # CORRECT EVENT: margin − spread
            z = (margin - home_spread) / LEAGUE_MARGIN_STD
            home_p = normal_cdf(z)
            away_p = 1 - home_p

            fair_home_d = 1 / home_p
            fair_away_d = 1 / away_p
            acc_home_d = 1 / (home_p * JUICE)
            acc_away_d = 1 / (away_p * JUICE)

            w.writerow({
                "game_id": gid,
                "date": r["date"],
                "time": r["time"],
                "away_team": away,
                "home_team": home,
                "away_team_proj_pts": away_pts,
                "home_team_proj_pts": home_pts,
                "away_spread": away_spread,
                "home_spread": home_spread,
                "away_ml_prob": float(a["win_probability"]),
                "home_ml_prob": float(h["win_probability"]),
                "away_spread_probability": round(away_p, 6),
                "home_spread_probability": round(home_p, 6),
                "fair_away_spread_decimal_odds": round(fair_away_d, 6),
                "fair_away_spread_american_odds": dec_to_amer(fair_away_d),
                "fair_home_spread_decimal_odds": round(fair_home_d, 6),
                "fair_home_spread_american_odds": dec_to_amer(fair_home_d),
                "acceptable_away_spread_decimal_odds": round(acc_away_d, 6),
                "acceptable_away_spread_american_odds": dec_to_amer(acc_away_d),
                "acceptable_home_spread_decimal_odds": round(acc_home_d, 6),
                "acceptable_home_spread_american_odds": dec_to_amer(acc_home_d),
                "league": "nba_spread"
            })

if __name__ == "__main__":
    main()
