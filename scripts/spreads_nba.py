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
            key = (r["team"], r["opponent"])
            games[key].append(r)

    out_path = OUTPUT_DIR / f"nba_spreads_market_{date_tag}.csv"

    fields = [
        "date",
        "time",
        "team",
        "opponent",
        "spread",
        "odds",
        "implied_prob",
        "fair_prob",
        "league",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for (team, opponent), rows in games.items():
            if len(rows) != 2:
                continue

            r1, r2 = rows

            p1 = amer_to_prob(float(r1["odds"]))
            p2 = amer_to_prob(float(r2["odds"]))

            total = p1 + p2
            p1_fair = p1 / total
            p2_fair = p2 / total

            w.writerow({
                "date": r1["date"],
                "time": r1["time"],
                "team": r1["team"],
                "opponent": r1["opponent"],
                "spread": r1["spread"],
                "odds": r1["odds"],
                "implied_prob": round(p1, 6),
                "fair_prob": round(p1_fair, 6),
                "league": r1["league"],
            })

            w.writerow({
                "date": r2["date"],
                "time": r2["time"],
                "team": r2["team"],
                "opponent": r2["opponent"],
                "spread": r2["spread"],
                "odds": r2["odds"],
                "implied_prob": round(p2, 6),
                "fair_prob": round(p2_fair, 6),
                "league": r2["league"],
            })

if __name__ == "__main__":
    main()
