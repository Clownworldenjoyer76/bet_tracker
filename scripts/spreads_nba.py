#!/usr/bin/env python3

import csv
import math
from pathlib import Path

# =========================
# Paths
# =========================
TOTALS_DIR = Path("docs/win/nba")
EDGE_DIR = Path("docs/win/edge")
SPREADS_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# Constants (added)
# =========================
LEAGUE_STD = 7.2
JUICE = 1.047619
EPS = 1e-6

# =========================
# Helpers
# =========================
def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def clamp(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

# =========================
# Main
# =========================
def main():
    totals_file = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))[-1]
    edge_file = sorted(EDGE_DIR.glob("edge_nba_*.csv"))[-1]
    spreads_file = sorted(SPREADS_DIR.glob("norm_dk_nba_spreads_*.csv"))[-1]

    with totals_file.open(newline="", encoding="utf-8") as f:
        totals = list(csv.DictReader(f))

    mm, dd, yyyy = totals[0]["date"].split("/")
    out_path = OUTPUT_DIR / f"edge_nba_spreads_{yyyy}_{mm.zfill(2)}_{dd.zfill(2)}.csv"

    edge_by_game = {}
    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            edge_by_game.setdefault(r["game_id"], {})[r["team"]] = r

    spread_by_team = {}
    with spreads_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            spread_by_team[r["team"]] = float(r["spread"])

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

            if gid not in edge_by_game:
                continue
            if away not in edge_by_game[gid] or home not in edge_by_game[gid]:
                continue
            if away not in spread_by_team or home not in spread_by_team:
                continue

            a = edge_by_game[gid][away]
            h = edge_by_game[gid][home]

            away_pts = float(a["points"])
            home_pts = float(h["points"])

            away_ml = float(a["win_probability"])
            home_ml = float(h["win_probability"])

            away_spread = float(spread_by_team[away])
            home_spread = float(spread_by_team[home])

            proj_margin = home_pts - away_pts

            home_cover = clamp(
                normal_cdf((proj_margin + home_spread) / LEAGUE_STD)
            )
            away_cover = clamp(1.0 - home_cover)

            fair_home_dec = 1.0 / home_cover
            fair_away_dec = 1.0 / away_cover

            acc_home_dec = 1.0 / (home_cover * JUICE)
            acc_away_dec = 1.0 / (away_cover * JUICE)

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
                "away_spread_probability": round(away_cover, 6),
                "home_spread_probability": round(home_cover, 6),
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
