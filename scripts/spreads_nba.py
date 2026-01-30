#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import defaultdict

INPUT_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def amer_to_prob(amer: float) -> float:
    if amer < 0:
        return -amer / (-amer + 100.0)
    return 100.0 / (amer + 100.0)

def main():
    infile = sorted(INPUT_DIR.glob("norm_dk_nba_spreads_*.csv"))[-1]
    date_tag = infile.stem.split("_")[-1]

    games = defaultdict(list)

    with infile.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["date"], r["time"], r["team"], r["opponent"])
            games[(r["date"], r["time"], frozenset([r["team"], r["opponent"]]))].append(r)

    out_path = OUTPUT_DIR / f"nba_spreads_market_{date_tag}.csv"

    fields = [
        "date","time",
        "home_team","away_team",
        "home_spread","away_spread",
        "home_odds","away_odds",
        "home_implied_prob","away_implied_prob",
        "home_fair_prob","away_fair_prob",
        "league"
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for (_, _, teams), rows in games.items():
            if len(rows) != 2:
                continue

            r1, r2 = rows

            if float(r1["spread"]) < 0:
                fav, dog = r1, r2
            else:
                fav, dog = r2, r1

            fav_prob = amer_to_prob(float(fav["odds"]))
            dog_prob = amer_to_prob(float(dog["odds"]))

            total = fav_prob + dog_prob
            fav_fair = fav_pro
