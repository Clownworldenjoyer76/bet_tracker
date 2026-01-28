#!/usr/bin/env python3
"""
scripts/nhl_spreads_04.py

Purpose:
- Populate FAIR puck line odds for UNDERDOG +1.5 only
- Calculates ONLY:
    - puck_line_fair_deci
    - puck_line_fair_amer

Authoritative goal source:
- docs/win/final/final_nhl_YYYY_MM_DD.csv

No juice. No sportsbook pricing. No personal edge logic.
"""

import csv
from pathlib import Path
import sys
import math
import re

SPREADS_DIR = Path("docs/win/nhl/spreads")
FINAL_DIR = Path("docs/win/final")

MAX_GOALS = 15  # safe Poisson cutoff for NHL scoring


def extract_date(filename: str) -> str:
    match = re.search(r"(\d{4}_\d{2}_\d{2})", filename)
    if not match:
        raise ValueError(f"Could not extract date from filename: {filename}")
    return match.group(1)


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def fair_prob_underdog_plus_1_5(lam_u: float, lam_f: float) -> float:
    """
    P(underdog goals - favorite goals >= -1)
    """
    prob = 0.0
    for u in range(MAX_GOALS + 1):
        pu = poisson_pmf(u, lam_u)
        for f in range(MAX_GOALS + 1):
            if u - f >= -1:
                prob += pu * poisson_pmf(f, lam_f)
    return prob


def deci_to_american(deci: float) -> int:
    if deci >= 2.0:
        return int(round(100 * (deci - 1)))
    else:
        return int(round(-100 / (deci - 1)))


def load_goal_map(final_path: Path):
    """
    Returns:
        dict[(game_id, team)] -> goals (float)
    """
    with final_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {
            (r["game_id"], r["team"]): float(r["goals"])
            for r in reader
        }


def process_file(spread_path: Path):
    date_str = extract_date(spread_path.name)
    final_path = FINAL_DIR / f"final_nhl_{date_str}.csv"

    if not final_path.exists():
        raise FileNotFoundError(f"Missing final file: {final_path}")

    goal_map = load_goal_map(final_path)

    with spread_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    for row in rows:
        gid = row["game_id"]
        away = row["away_team"]
        home = row["home_team"]
        underdog = row["underdog"]

        try:
            away_goals = goal_map[(gid, away)]
            home_goals = goal_map[(gid, home)]
        except KeyError:
            # strict join failure — do not fabricate
            continue

        if underdog == away:
            lam_u = away_goals
            lam_f = home_goals
        else:
            lam_u = home_goals
            lam_f = away_goals

        p = fair_prob_underdog_plus_1_5(lam_u, lam_f)

        fair_deci = 1.0 / p
        fair_amer = deci_to_american(fair_deci)

        row["puck_line_fair_deci"] = f"{fair_deci:.6f}"
        row["puck_line_fair_amer"] = str(fair_amer)

    with spread_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated fair puck line odds: {spread_path.name}")


def main():
    files = sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))

    if not files:
        print("No nhl_spreads files found.", file=sys.stderr)
        sys.exit(1)

    for f in files:
        process_file(f)


if __name__ == "__main__":
    main()
