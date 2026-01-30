#!/usr/bin/env python3
"""
spreads_nba.py

Build NBA spread markets from GAME-LEVEL totals file, but derive the
spread (margin) and probabilities from the SAME underlying moneyline model outputs
to prevent contradictions.

Inputs:
- docs/win/nba/edge_nba_totals_YYYY_MM_DD.csv   (game-level, has team_1/team_2)
- docs/win/final/final_nba_YYYY_MM_DD.csv      (team-level, has points + win_probability)

Conventions:
- away_team = team_1 (from totals file)
- home_team = team_2 (from totals file)

Output (team-level, 2 rows per game_id):
- docs/win/nba/spreads/edge_nba_spreads_YYYY_MM_DD.csv
"""

import csv
import math
import re
from pathlib import Path
from typing import Dict, Tuple, List

# ============================================================
# PATHS
# ============================================================

TOTALS_DIR = Path("docs/win/nba")
FINAL_DIR = Path("docs/win/final")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# PRICING / SAFETY FIXES
# ============================================================

EDGE_BUFFER = 0.05
MARGIN_STD_DEV = 12.0     # NBA margin std dev (tunable)
MAX_SPREAD = 8.5          # FIX #1: cap absurd spreads
MIN_PROB = 0.12           # FIX #2: probability floor prevents insane odds

# ============================================================
# HELPERS
# ============================================================

def extract_yyyymmdd(filename: str) -> str:
    m = re.search(r"(\d{4}_\d{2}_\d{2})", filename)
    if not m:
        raise ValueError(f"Could not extract date from: {filename}")
    return m.group(1)

def force_half_point(x: float) -> float:
    rounded = round(x * 2) / 2
    if float(rounded).is_integer():
        return rounded + 0.5
    return rounded

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def cover_prob(mean_margin: float, spread_for_team: float) -> float:
    """
    mean_margin: expected (away - home)
    spread_for_team: the team's spread value from its perspective
                     (favorite negative, dog positive)

    A bet on a team at spread S wins if:
        team_score - opp_score + S > 0
    In margin terms (away - home):
        if team is away:
            margin + S > 0  => margin > -S
        if team is home:
            (-margin) + S > 0 => margin < S  (handled by using mean = -mean_margin)

    We implement both teams by passing mean_margin appropriately and using:
        P(X > threshold) with X ~ Normal(mean_margin, sd)
    """
    threshold = -spread_for_team
    z = (mean_margin - threshold) / MARGIN_STD_DEV
    return normal_cdf(z)

def compress_tail(p: float) -> float:
    """
    FIX #3: compress extremes so spreads don't go totally detached from ML intuition.
    Keeps ordering but reduces insane tails.
    """
    if p > 0.5:
        return 0.5 + 0.75 * (p - 0.5)
    return p

def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))

def fair_decimal(p: float) -> float:
    return 1.0 / max(p, 0.0001)

def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER, 0.0001)

def load_final_map(final_path: Path) -> Dict[Tuple[str, str], dict]:
    """
    Map (game_id, team) -> row from final_nba_*.csv
    Must contain points and win_probability for pricing consistency.
    """
    m: Dict[Tuple[str, str], dict] = {}
    with final_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            gid = row.get("game_id")
            team = row.get("team")
            if not gid or not team:
                continue
            m[(gid, team)] = row
    return m

# ============================================================
# MAIN
# ============================================================

def main():
    totals_files = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))
    if not totals_files:
        raise FileNotFoundError("No docs/win/nba/edge_nba_totals_*.csv files found")

    totals_path = totals_files[-1]
    date_str = extract_yyyymmdd(totals_path.name)

    final_path = FINAL_DIR / f"final_nba_{date_str}.csv"
    if not final_path.exists():
        raise FileNotFoundError(f"Missing moneyline-derived final file: {final_path}")

    final_map = load_final_map(final_path)

    out_path = OUTPUT_DIR / f"edge_nba_spreads_{date_str}.csv"

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

    out_rows: List[dict] = []

    with totals_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"game_id", "date", "time", "team_1", "team_2"}
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{totals_path.name} missing required columns: {missing}")

        for trow in reader:
            gid = trow.get("game_id")
            away = trow.get("team_1")
            home = trow.get("team_2")

            if not gid or not away or not home:
                continue

            away_final = final_map.get((gid, away))
            home_final = final_map.get((gid, home))
            if not away_final or not home_final:
                # strict join: if your naming differs even slightly, you WANT to skip
                continue

            try:
                pts_away = float(away_final["points"])
                pts_home = float(home_final["points"])
            except Exception:
                continue

            # expected margin in AWAY-HOME space
            mean_margin = pts_away - pts_home

            # Build spread from projected margin (capped, forced .5)
            raw = min(abs(mean_margin), MAX_SPREAD)
            spread_abs = force_half_point(raw)

            # Determine favorite by projected points
            away_is_fav = mean_margin > 0
            away_spread = -spread_abs if away_is_fav else spread_abs
            home_spread = -away_spread

            # COVER probabilities from SAME projected margin base
            p_away_cover = cover_prob(mean_margin=mean_margin, spread_for_team=away_spread)
            p_home_cover = cover_prob(mean_margin=-mean_margin, spread_for_team=home_spread)

            # compress extremes + floor
            p_away_cover = max(compress_tail(p_away_cover), MIN_PROB)
            p_home_cover = max(compress_tail(p_home_cover), MIN_PROB)

            # price away
            fair_d = fair_decimal(p_away_cover)
            acc_d = acceptable_decimal(p_away_cover)

            out_rows.append({
                "game_id": gid,
                "date": trow.get("date", ""),
                "time": trow.get("time", ""),
                "team": away,
                "opponent": home,
                "spread": away_spread,
                "model_probability": round(p_away_cover, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

            # price home
            fair_d = fair_decimal(p_home_cover)
            acc_d = acceptable_decimal(p_home_cover)

            out_rows.append({
                "game_id": gid,
                "date": trow.get("date", ""),
                "time": trow.get("time", ""),
                "team": home,
                "opponent": away,
                "spread": home_spread,
                "model_probability": round(p_home_cover, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": decimal_to_american(fair_d),
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": decimal_to_american(acc_d),
                "league": "nba_spread",
            })

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Created {out_path} ({len(out_rows)} rows)")

if __name__ == "__main__":
    main()
