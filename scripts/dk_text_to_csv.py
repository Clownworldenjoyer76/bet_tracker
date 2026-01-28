import csv
import sys
from datetime import datetime

LEAGUE = sys.argv[1] if len(sys.argv) > 1 else "ncaab"
DATE = datetime.now().strftime("%Y_%m_%d")

OUT_ML = f"docs/win/manual/dk_{LEAGUE}_moneyline_{DATE}.csv"
OUT_SP = f"docs/win/manual/dk_{LEAGUE}_spreads_{DATE}.csv"
OUT_OU = f"docs/win/manual/dk_{LEAGUE}_totals_{DATE}.csv"


with open("raw.txt") as f:
    lines = [l.strip().replace("opens in a new tab", "") for l in f if l.strip()]

ml_rows, sp_rows, ou_rows = [], [], []

i = 0
while i < len(lines):

    if "@" not in lines[i]:
        i += 1
        continue

    away, home = [x.strip() for x in lines[i].split("@", 1)]
    date_str, time_str = [x.strip() for x in lines[i+1].split(",", 1)]
    i += 2

    while i < len(lines) and lines[i] in ("Moneyline", "Spread", "Total"):
        market = lines[i]
        i += 1

        if lines[i:i+3] != ["Odds", "% Handle", "% Bets"]:
            raise SystemExit(f"header mismatch after {market}")
        i += 3

        a = lines[i:i+4]
        b = lines[i+4:i+8]
        i += 8

        if market == "Moneyline":
            t1, o1, h1, b1 = a
            t2, o2, h2, b2 = b

            ml_rows.append([date_str, time_str, t1, away, o1, h1.rstrip("%"), b1.rstrip("%"), LEAGUE])
            ml_rows.append([date_str, time_str, t2, home, o2, h2.rstrip("%"), b2.rstrip("%"), LEAGUE])

        elif market == "Spread":
            t1, o1, h1, b1 = a
            t2, o2, h2, b2 = b

            team1, spread1 = t1.rsplit(" ", 1)
            team2, spread2 = t2.rsplit(" ", 1)

            sp_rows.append([date_str, time_str, team1, team2, spread1, o1, h1.rstrip("%"), b1.rstrip("%"), f"{LEAGUE}_spreads"])
            sp_rows.append([date_str, time_str, team2, team1, spread2, o2, h2.rstrip("%"), b2.rstrip("%"), f"{LEAGUE}_spreads"])

        elif market == "Total":
            s1, o1, h1, b1 = a
            s2, o2, h2, b2 = b

            side1, total = s1.split(" ", 1)
            side2, _ = s2.split(" ", 1)

            ou_rows.append([date_str, time_str, away, home, side1, total, o1, h1.rstrip("%"), b1.rstrip("%"), f"{LEAGUE}_ou"])
            ou_rows.append([date_str, time_str, away, home, side2, total, o2, h2.rstrip("%"), b2.rstrip("%"), f"{LEAGUE}_ou"])
            ou_rows.append([date_str, time_str, home, away, side1, total, o1, h1.rstrip("%"), b1.rstrip("%"), f"{LEAGUE}_ou"])
            ou_rows.append([date_str, time_str, home, away, side2, total, o2, h2.rstrip("%"), b2.rstrip("%"), f"{LEAGUE}_ou"])

# WRITE FILES
if ml_rows:
    with open(OUT_ML, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date","time","team","opponent","odds","handle_pct","bets_pct","league"])
        w.writerows(ml_rows)

if sp_rows:
    with open(OUT_SP, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date","time","team","opponent","spread","odds","handle_pct","bets_pct","league"])
        w.writerows(sp_rows)

if ou_rows:
    with open(OUT_OU, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date","time","team","opponent","side","total","odds","handle_pct","bets_pct","league"])
        w.writerows(ou_rows)
