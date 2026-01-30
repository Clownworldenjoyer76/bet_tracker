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

def round_half(x: float) -> float:
    return round(x * 2) / 2

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

def clamp_prob(p: float) -> float:
    if p < EPS:
        return EPS
    if p > 1.0 - EPS:
        return 1.0 - EPS
    return p

def main():
    totals_files = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))
    if not totals_files:
        raise FileNotFoundError("No input totals files found: docs/win/nba/edge_nba_totals_*.csv")

    totals_file = totals_files[-1]
    with totals_file.open(newline="", encoding="utf-8") as f:
        totals = list(csv.DictReader(f))

    if not totals:
        raise ValueError(f"Totals file is empty: {totals_file}")

    raw_date = totals[0].get("date", "")
    if not raw_date:
        raise ValueError("Missing 'date' in first totals row")

    # Expecting MM/DD/YYYY in totals; output requires YYYY_MM_DD
    parts = raw_date.split("/")
    if len(parts) != 3:
        raise ValueError(f"Unsupported date format in totals: {raw_date}")
    mm, dd, yyyy = parts[0].zfill(2), parts[1].zfill(2), parts[2]
    out_path = OUTPUT_DIR / f"edge_nba_spreads_{yyyy}_{mm}_{dd}.csv"

    edge_files = sorted(EDGE_DIR.glob("edge_nba_*.csv"))
    if not edge_files:
        raise FileNotFoundError("No input edge files found: docs/win/edge/edge_nba_*.csv")

    edge_file = edge_files[-1]
    edge_by_game = {}
    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gid = r.get("game_id")
            if not gid:
                continue
            edge_by_game.setdefault(gid, []).append(r)

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
            gid = r.get("game_id", "")
            away = r.get("team_1", "")
            home = r.get("team_2", "")
            if not gid or not away or not home:
                continue

            rows = edge_by_game.get(gid)
            if not rows:
                continue

            away_row = None
            home_row = None
            for rr in rows:
                if rr.get("team") == away:
                    away_row = rr
                elif rr.get("team") == home:
                    home_row = rr

            if away_row is None or home_row is None:
                continue

            away_pts = float(away_row["points"])
            home_pts = float(home_row["points"])

            away_ml = float(away_row["win_probability"])
            home_ml = float(home_row["win_probability"])

            # Projected margin (home - away)
            proj_margin = home_pts - away_pts

            # SPREAD SIGN FIX:
            # Negative spread assigned to projected winner, regardless of venue.
            spread_mag = round_half(abs(proj_margin))
            if proj_margin > 0:
                # Home projected winner => home negative
                home_spread = -spread_mag
                away_spread = spread_mag
            elif proj_margin < 0:
                # Away projected winner => away negative
                away_spread = -spread_mag
                home_spread = spread_mag
            else:
                # exact tie
                home_spread = 0.0
                away_spread = 0.0

            # PROBABILITY EVENT FIX:
            # Home covers if final_margin + home_spread > 0
            # With Normal(final_margin ~ N(proj_margin, LEAGUE_STD^2)):
            home_prob = normal_cdf((proj_margin + home_spread) / LEAGUE_STD)
            home_prob = clamp_prob(home_prob)
            away_prob = clamp_prob(1.0 - home_prob)

            fair_home_dec = 1.0 / home_prob
            fair_away_dec = 1.0 / away_prob

            acc_home_dec = 1.0 / (home_prob * JUICE)
            acc_away_dec = 1.0 / (away_prob * JUICE)

            w.writerow({
                "game_id": gid,
                "date": r.get("date", ""),
                "time": r.get("time", ""),
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
