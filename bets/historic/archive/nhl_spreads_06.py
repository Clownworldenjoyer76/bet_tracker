#!/usr/bin/env python3
"""
nhl_spreads_06.py

Adds spread_win_prob for +1.5 puck line.

Definition:
P(+1.5) = P(underdog wins) + P(underdog loses by exactly 1)

Method:
- Independent Poisson goal model
- Expected goals already provided (home_goals, away_goals)
- Win probability already provided
- Compute P(lose by exactly 1) via Poisson convolution
"""

import csv
import math
from pathlib import Path

INPUT_DIR = Path("docs/win/nhl/spreads")
OUTPUT_DIR = INPUT_DIR  # in-place overwrite

# --------------------------------------------------
# Poisson PMF
# --------------------------------------------------
def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


# --------------------------------------------------
# P(underdog loses by exactly 1)
# --------------------------------------------------
def prob_lose_by_one(lam_dog: float, lam_fav: float, max_goals: int = 12) -> float:
    """
    Sum P(dog = k, fav = k+1) for k = 0..max_goals
    """
    p = 0.0
    for k in range(max_goals + 1):
        p += poisson_pmf(k, lam_dog) * poisson_pmf(k + 1, lam_fav)
    return p


def compute_plus_one_five_prob(
    dog_win_prob: float,
    lam_dog: float,
    lam_fav: float
) -> float:
    """
    P(+1.5) = P(win) + P(lose by 1)
    """
    p_lose_1 = prob_lose_by_one(lam_dog, lam_fav)
    return min(dog_win_prob + p_lose_1, 0.9999)


# --------------------------------------------------
# MAIN
# --------------------------------------------------
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
