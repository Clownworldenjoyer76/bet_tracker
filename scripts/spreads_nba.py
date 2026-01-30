#!/usr/bin/env python3

import csv
import math
from pathlib import Path
from collections import defaultdict

# ============================================================
# PATHS
# ============================================================

TOTALS_DIR = Path("docs/win/nba")
EDGE_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# CONSTANTS
# ============================================================

LEAGUE_MARGIN_STD = 7.2
JUICE_MULTIPLIER = 1.047619

# ============================================================
# HELPERS
# ============================================================

def round_half(x: float) -> float:
    return round(x * 2) / 2

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def decimal_to_american(d: float) -> int:
    if d >= 2:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))

# ============================================================
# MAIN
# ============================================================

def main():
    totals_files = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))
    if not totals_files:
        raise FileNotFoundError("No edge_nba_totals files found")

    totals_path = totals_files[-1]

    # Load totals rows
    with totals_path.open(newline="", encoding="utf-8") as f:
        totals_rows = list(csv.DictReader(f))

    if not totals_rows:
        return

    # Output date from first row
    raw_date = totals_rows[0]["date"]
    date_str = raw_date.replace("/", "_")
    out_path = OUTPUT_DIR / f"edge_nba_spreads_{date_str}.csv"

    # Load edge_nba projections
    edge_files = sorted(EDGE_DIR.glob("edge_nba_*.csv"))
    if not edge_files:
        raise FileNotFoundError("No edge_nba files found")

    edge_path = edge_files[-1]

    edge_map = {}
    with edge_path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            edge_map[(r["game_id"], r["team"])] = r

    fieldnames = [
        "game_id",
        "date",
        "time",
        "away_team",
        "home_team",
        "away_team_proj_pts",
        "home_team_proj_pts",
        "away_spread",
        "home_spread",
        "away_ml_prob",
        "home_ml_prob",
        "away_spread_probability",
        "home_spread_probability",
        "fair_away_spread_decimal_odds",
        "fair_away_spread_american_odds",
        "fair_home_spread_decimal_odds",
        "fair_home_spread_american_odds",
        "acceptable_away_spread_decimal_odds",
        "acceptable_away_spread_american_odds",
        "acceptable_home_spread_decimal_odds",
        "acceptable_home_spread_american_odds",
        "league",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in totals_rows:
            gid = row["game_id"]
            away = row["team_1"]
            home = row["team_2"]

            away_edge = edge_map.get((gid, away))
            home_edge = edge_map.get((gid, home))
            if not away_edge or not home_edge:
                continue

            away_pts = float(away_edge["points"])
            home_pts = float(home_edge["points"])

            margin = home_pts - away_pts

            home_spread = round_half(margin)
            away_spread = -home_spread

            # ---- probabilities ----
            z = (home_spread - margin) / LEAGUE_MARGIN_STD
            home_prob = 1 - normal_cdf(z)
            away_prob = 1 - home_prob

            # ---- fair odds ----
            fair_home_dec = 1 / home_prob
            fair_away_dec = 1 / away_prob

            # ---- acceptable odds (juice) ----
            acc_home_dec = 1 / (home_prob * JUICE_MULTIPLIER)
            acc_away_dec = 1 / (away_prob * JUICE_MULTIPLIER)

            writer.writerow({
                "game_id": gid,
                "date": row["date"],
                "time": row["time"],
                "away_team": away,
                "home_team": home,
                "away_team_proj_pts": away_pts,
                "home_team_proj_pts": home_pts,
                "away_spread": away_spread,
                "home_spread": home_spread,
                "away_ml_prob": float(away_edge["win_probability"]),
                "home_ml_prob": float(home_edge["win_probability"]),
                "away_spread_probability": round(away_prob, 6),
                "home_spread_probability": round(home_prob, 6),
                "fair_away_spread_decimal_odds": round(fair_away_dec, 6),
                "fair_away_spread_american_odds": decimal_to_american(fair_away_dec),
                "fair_home_spread_decimal_odds": round(fair_home_dec, 6),
                "fair_home_spread_american_odds": decimal_to_american(fair_home_dec),
                "acceptable_away_spread_decimal_odds": round(acc_away_dec, 6),
                "acceptable_away_spread_american_odds": decimal_to_american(acc_away_dec),
                "acceptable_home_spread_decimal_odds": round(acc_home_dec, 6),
                "acceptable_home_spread_american_odds": decimal_to_american(acc_home_dec),
                "league": "nba_spread",
            })

    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
