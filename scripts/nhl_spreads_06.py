#!/usr/bin/env python3
"""
nhl_spreads_06.py

Adds spread_win_prob for +1.5 puck line.

Definition:
P(+1.5) = P(underdog wins) + P(underdog loses by exactly 1)

Method:
- Use Poisson goal model with Skellam approximation
- Expected goals already provided (home_goals, away_goals)
- Win probability already provided (away_win_prob / home_win_prob)
- Compute P(loss by exactly 1) analytically
"""

import csv
import math
from pathlib import Path
from collections import defaultdict

INPUT_DIR = Path("docs/win/nhl/spreads")
OUTPUT_DIR = INPUT_DIR  # in-place overwrite

# --------------------------------------------------
# Skellam PMF for k = -1 (lose by exactly 1)
# --------------------------------------------------
def skellam_pmf_minus_one(lam_dog: float, lam_fav: float) -> float:
    """
    P(D = -1) where D = goals_dog - goals_fav
    """
    if lam_dog <= 0 or lam_fav <= 0:
        return 0.0

    term = math.exp(-(lam_dog + lam_fav))
    ratio = math.sqrt(lam_dog / lam_fav)
    bessel = math.i1(2 * math.sqrt(lam_dog * lam_fav))
    return term * ratio * bessel


def compute_plus_one_five_prob(
    dog_win_prob: float,
    lam_dog: float,
    lam_fav: float
) -> float:
    """
    P(+1.5) = P(win) + P(lose by 1)
    """
    p_lose_by_one = skellam_pmf_minus_one(lam_dog, lam_fav)
    return min(dog_win_prob + p_lose_by_one, 0.9999)


def main():
    files = sorted(INPUT_DIR.glob("nhl_spreads_*.csv"))
    if not files:
        raise FileNotFoundError("No nhl_spreads_*.csv files found")

    path = files[-1]

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "spread_win_prob" not in fieldnames:
        fieldnames.append("spread_win_prob")

    out_rows = []

    for r in rows:
        try:
            away = r["away_team"]
            home = r["home_team"]

            away_win = float(r["away_win_prob"])
            home_win = float(r["home_win_prob"])

            away_goals = float(r["away_goals"])
            home_goals = float(r["home_goals"])

            underdog = r.get("underdog", "")
        except Exception:
            r["spread_win_prob"] = ""
            out_rows.append(r)
            continue

        if underdog == away:
            p = compute_plus_one_five_prob(
                dog_win_prob=away_win,
                lam_dog=away_goals,
                lam_fav=home_goals
            )
        elif underdog == home:
            p = compute_plus_one_five_prob(
                dog_win_prob=home_win,
                lam_dog=home_goals,
                lam_fav=away_goals
            )
        else:
            p = ""

        r["spread_win_prob"] = f"{p:.4f}" if p != "" else ""
        out_rows.append(r)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Updated {path} with spread_win_prob")


if __name__ == "__main__":
    main()
