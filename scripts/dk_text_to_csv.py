import csv, os
from datetime import datetime

league = os.environ["LEAGUE"]
date = datetime.now().strftime("%Y_%m_%d")

OUT_ML = f"docs/win/manual/dk_{league}_ML_{date}.csv"
OUT_SP = f"docs/win/manual/dk_{league}_spreads_{date}.csv"
OUT_TOT = f"docs/win/manual/dk_{league}_totals_{date}.csv"

with open("raw.txt") as f:
    lines = [l.strip().replace("opens in a new tab","") for l in f if l.strip()]

ml_rows, sp_rows, tot_rows = [], [], []
i = 0

while i < len(lines):
    # ---------- GAME HEADER ----------
    if "@" not in lines[i]:
        i += 1
        continue

    away, home = [x.strip() for x in lines[i].split("@", 1)]
    date_str, time_str = [x.strip() for x in lines[i+1].split(",", 1)]
    i += 2

    # ---------- MARKETS INSIDE GAME ----------
    while i < len(lines) and "@" not in lines[i]:

        # ===== MONEYLINE =====
        if lines[i] == "Moneyline":
            i += 4  # skip headers

            t1, o1, h1, b1 = lines[i:i+4]
            t2, o2, h2, b2 = lines[i+4:i+8]
            i += 8

            ml_rows.append([date_str,time_str,t1,away,o1,h1.rstrip("%"),b1.rstrip("%"),league])
            ml_rows.append([date_str,time_str,t2,home,o2,h2.rstrip("%"),b2.rstrip("%"),league])

        # ===== SPREAD =====
        elif lines[i] == "Spread":
            i += 4

            t1, o1, h1, b1 = lines[i:i+4]
            t2, o2, h2, b2 = lines[i+4:i+8]
            i += 8

            team1, spread1 = t1.rsplit(" ",1)
            team2, spread2 = t2.rsplit(" ",1)

            sp_rows.append([date_str,time_str,team1,team2,spread1,o1,h1.rstrip("%"),b1.rstrip("%"),f"{league}_spreads"])
            sp_rows.append([date_str,time_str,team2,team1,spread2,o2,h2.rstrip("%"),b2.rstrip("%"),f"{league}_spreads"])

        # ===== TOTALS =====
        elif lines[i] == "Total":
            i += 4

            s1, o1, h1, b1 = lines[i:i+4]
            s2, o2, h2, b2 = lines[i+4:i+8]
            i += 8

            side1, total = s1.split(" ",1)
            side2, _ = s2.split(" ",1)

            for team, opp in [(away,home),(home,away)]:
                tot_rows.append([date_str,time_str,team,opp,side1,total,o1,h1.rstrip("%"),b1.rstrip("%"),f"{league}_ou"])
                tot_rows.append([date_str,time_str,team,opp,side2,total,o2,h2.rstrip("%"),b2.rstrip("%"),f"{league}_ou"])

        else:
            i += 1

# ---------- WRITE FILES ----------
if ml_rows:
    with open(OUT_ML,"w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["date","time","team","opponent","odds","handle_pct","bets_pct","league"])
        w.writerows(ml_rows)

if sp_rows:
    with open(OUT_SP,"w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["date","time","team","opponent","spread","odds","handle_pct","bets_pct","league"])
        w.writerows(sp_rows)

if tot_rows:
    with open(OUT_TOT,"w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["date","time","team","opponent","side","total","odds","handle_pct","bets_pct","league"])
        w.writerows(tot_rows)
