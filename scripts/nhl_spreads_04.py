#!/usr/bin/env python3
"""
scripts/nhl_spreads_04.py

Purpose:
- Populate fair puck line odds for UNDERDOG +1.5 only
- Calculates:
    - puck_line_fair_deci
    - puck_line_fair_amer

Inputs (must already exist in CSV):
- underdog
- away_team
- home_team
- away_goals   (expected goals)
- home_goals   (expected goals)

No juice. No sportsbook pricing. No personal edge logic.
"""

import csv
from pathlib import Path
import sys
import math

SPREADS_DIR = Path("docs/win/nhl/spreads")

MAX_GOALS = 15  # safe upper bound for NHL Poisson mass


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


def process_file(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    for row in rows:
        underdog = row["underdog"]

        if underdog == row["away_team"]:
            lam_u = float(row["away_goals"])
            lam_f = float(row["home_goals"])
        else:
            lam_u = float(row["home_goals"])
            lam_f = float(row["away_goals"])

        p = fair_prob_underdog_plus_1_5(lam_u, lam_f)

        fair_deci = 1.0 / p
        fair_amer = deci_to_american(fair_deci)

        row["puck_line_fair_deci"] = f"{fair_deci:.6f}"
        row["puck_line_fair_amer"] = str(fair_amer)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated fair puck line odds: {path.name}")


def main():
    files = sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))

    if not files:
        print("No nhl_spreads files found.", file=sys.stderr)
        sys.exit(1)

    for f in files:
        process_file(f)


if __name__ == "__main__":
    main()
