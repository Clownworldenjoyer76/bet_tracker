#scripts/dk_text_to_csv.py
#!/usr/bin/env python3

import csv
import sys
import os
from datetime import datetime

LEAGUE = sys.argv[1] if len(sys.argv) > 1 else "ncaab"
DATE = datetime.now().strftime("%Y_%m_%d")

OUT_DIR = "docs/win/manual/cleaned"
os.makedirs(OUT_DIR, exist_ok=True)

OUT_ML = f"{OUT_DIR}/dk_{LEAGUE}_moneyline_{DATE}.csv"
OUT_SP = f"{OUT_DIR}/dk_{LEAGUE}_spreads_{DATE}.csv"
OUT_OU = f"{OUT_DIR}/dk_{LEAGUE}_totals_{DATE}.csv"


# ======================
# NORMALIZATION
# ======================

def clean(line: str) -> str:
    return (
        line.replace("opens in a new tab", "")
            .replace("−", "-")
            .strip()
    )


with open("raw.txt", encoding="utf-8") as f:
    lines = [clean(l) for l in f if clean(l)]


ml_rows, sp_rows, ou_rows = [], [], []

i = 0
while i < len(lines):

    # game header
    if "@" not in lines[i]:
        i += 1
        continue

    away, home = [x.strip() for x in lines[i].split("@", 1)]

    # date / time
    if i + 1 >= len(lines):
        break

    date_str, time_str = [x.strip() for x in lines[i + 1].split(",", 1)]
    i += 2

    # markets
    while i < len(lines) and lines[i] in ("Moneyline", "Spread", "Total", "Puck Line"):
        market = lines[i]
        normalized = "Spread" if market == "Puck Line" else market
        i += 1

        # header sanity
        if lines[i:i + 3] != ["Odds", "% Handle", "% Bets"]:
            break
        i += 3

        if i + 7 >= len(lines):
            break

        a = lines[i:i + 4]
        b = lines[i + 4:i + 8]
        i += 8

        # ======================
        # MONEYLINE
        # ======================
        if normalized == "Moneyline":
            t1, o1, h1, b1 = a
            t2, o2, h2, b2 = b

            opp1 = home if t1 == away else away
            opp2 = home if t2 == away else away

            ml_rows.append([
                date_str, time_str, t1, opp1,
                o1, h1.rstrip("%"), b1.rstrip("%"), LEAGUE
            ])
            ml_rows.append([
                date_str, time_str, t2, opp2,
                o2, h2.rstrip("%"), b2.rstrip("%"), LEAGUE
            ])

        # ======================
        # SPREAD
        # ======================
        elif normalized == "Spread":
            t1, o1, h1, b1 = a
            t2, o2, h2, b2 = b

            team1, spread1 = t1.rsplit(" ", 1)
            team2, spread2 = t2.rsplit(" ", 1)

            sp_rows.append([
                date_str, time_str, team1, team2,
                spread1, o1, h1.rstrip("%"), b1.rstrip("%"),
                f"{LEAGUE}_spreads"
            ])
            sp_rows.append([
                date_str, time_str, team2, team1,
                spread2, o2, h2.rstrip("%"), b2.rstrip("%"),
                f"{LEAGUE}_spreads"
            ])

        # ======================
        # TOTALS
        # ======================
        elif normalized == "Total":
            s1, o1, h1, b1 = a
            s2, o2, h2, b2 = b

            side1, total = s1.split(" ", 1)
            side2, _ = s2.split(" ", 1)

            ou_rows.append([
                date_str, time_str, away, home,
                side1, total, o1, h1.rstrip("%"), b1.rstrip("%"),
                f"{LEAGUE}_totals"
            ])
            ou_rows.append([
                date_str, time_str, away, home,
                side2, total, o2, h2.rstrip("%"), b2.rstrip("%"),
                f"{LEAGUE}_totals"
            ])
            ou_rows.append([
                date_str, time_str, home, away,
                side1, total, o1, h1.rstrip("%"), b1.rstrip("%"),
                f"{LEAGUE}_totals"
            ])
            ou_rows.append([
                date_str, time_str, home, away,
                side2, total, o2, h2.rstrip("%"), b2.rstrip("%"),
                f"{LEAGUE}_totals"
            ])


# ======================
# WRITE FILES
# ======================

if ml_rows:
    with open(OUT_ML, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "time", "team", "opponent", "odds", "handle_pct", "bets_pct", "league"])
        w.writerows(ml_rows)

if sp_rows:
    with open(OUT_SP, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "time", "team", "opponent", "spread", "odds", "handle_pct", "bets_pct", "league"])
        w.writerows(sp_rows)

if ou_rows:
    with open(OUT_OU, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "time", "team", "opponent", "side", "total", "odds", "handle_pct", "bets_pct", "league"])
        w.writerows(ou_rows)
