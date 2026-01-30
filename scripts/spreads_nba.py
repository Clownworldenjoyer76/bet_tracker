#!/usr/bin/env python3

import csv
import math
from pathlib import Path

TOTALS_DIR = Path("docs/win/nba")
EDGE_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_STD = 7.2
JUICE = 1.047619
EPS = 1e-6

def round_to_half_no_whole(x: float) -> float:
    r = round(x * 2) / 2
    if r.is_integer():
        return r + 0.5 if r > 0 else r - 0.5
    return r

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

def clamp_prob(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def main():
    totals_file = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))[-1]
    with totals_file.open(newline="", encoding="utf-8") as f:
        totals = list(csv.DictReader(f))

    mm, dd, yyyy = totals[0]["date"].split("/")
    out_path = OUTPUT_DIR / f"edge_nba_spreads_{yyyy}_{mm.zfill(2)}_{dd.zfill(2)}.csv"

    edge_file = sorted(EDGE_DIR.glob("edge_nba_*.csv"))[-1]
    edge_by_game = {}
    with edge_file.open(newline="", encoding="utf-8") as f:
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
            away = r["team_1"]
            home = r["team_2"]

            rows = edge_by_game.get(gid)
            if not rows or len(rows) != 2:
                continue

            if rows[0]["team"] == away:
                a, h = rows
            else:
                h, a = rows

            away_pts = float(a["points"])
            home_pts = float(h["points"])

            away_ml = float(a["win_probability"])
            home_ml = float(h["win_probability"])

            proj_margin = home_pts - away_pts
            spread_mag = round_to_half_no_whole(abs(proj_margin))

            if proj_margin > 0:
                home_spread = -spread_mag
                away_spread = spread_mag
            elif proj_margin < 0:
                away_spread = -spread_mag
                home_spread = spread_mag
            else:
                home_spread = -0.5
                away_spread = 0.5

            home_prob = normal_cdf((proj_margin + home_spread) / LEAGUE_STD)
            home_prob = clamp_prob(home_prob)
            away_prob = clamp_prob(1.0 - home_prob)

            fair_home_dec = 1.0 / home_prob
            fair_away_dec = 1.0 / away_prob
            acc_home_dec = 1.0 / (home_prob * JUICE)
            acc_away_dec = 1.0 / (away_prob * JUICE)

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
                "away_ml_prob": away_ml,
                "home_ml_prob": home_ml,
                "away_spread_probability": round(away_prob, 6),
                "home_spread_probability": round(home_prob, 6),
                "fair_away_spread_decimal_odds": round(fair_away_dec, 6),
                "fair_away_spread_american_odds": dec_to_amer(fair_away_dec),
                "fair_home_spread_decimal_odds": round(fair_home_dec, 6),
                "fair_home_spread_american_odds": dec_to_amer(fair_home_dec),
                "acceptable_away_spread_decimal_odds": round(acc_away_dec, 6),
                "acceptable_away_spread_american_odds": dec_to_amer(acc_away_dec),
                "acceptable_home_spread_decimal_odds": round(acc_home_dec, 6),
                "acceptable_home_spread_american_odds": dec_to_amer(acc_home_dec),
                "league": "nba_spread"
            })

if __name__ == "__main__":
    main()
