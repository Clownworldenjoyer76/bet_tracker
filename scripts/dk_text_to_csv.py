# scripts/dk_text_to_csv.py

## Parses raw DraftKings text into structured moneyline, spread, and totals CSV files
## for the given league and current date, and always writes a detailed summary/error log
## describing games detected, rows written, and any parsing issues.

#!/usr/bin/env python3

import csv
import sys
import os
from datetime import datetime
import traceback

LEAGUE = sys.argv[1] if len(sys.argv) > 1 else "ncaab"
DATE = datetime.now().strftime("%Y_%m_%d")

OUT_DIR = "docs/win/manual/first"
ERROR_DIR = "docs/win/errors/dk_input"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)

# filenames must remain standard (ncaab, not ncaab_dk)
FILE_LEAGUE = "ncaab" if LEAGUE == "ncaab_dk" else LEAGUE

OUT_ML = f"{OUT_DIR}/dk_{FILE_LEAGUE}_moneyline_{DATE}.csv"
OUT_SP = f"{OUT_DIR}/dk_{FILE_LEAGUE}_spreads_{DATE}.csv"
OUT_OU = f"{OUT_DIR}/dk_{FILE_LEAGUE}_totals_{DATE}.csv"

ERROR_LOG = f"{ERROR_DIR}/dk_input_{DATE}.txt"

ml_rows, sp_rows, ou_rows = [], [], []
games_seen = 0
errors = []

# ======================
# NORMALIZATION
# ======================

def clean(line: str) -> str:
    return (
        line.replace("opens in a new tab", "")
            .replace("−", "-")
            .strip()
    )

def write_summary():
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("DK INPUT PARSE SUMMARY\n")
        f.write("======================\n\n")
        f.write(f"League: {LEAGUE}\n")
        f.write(f"Date: {DATE}\n")
        f.write(f"Games detected: {games_seen}\n")
        f.write(f"Moneyline rows: {len(ml_rows)}\n")
        f.write(f"Spread rows: {len(sp_rows)}\n")
        f.write(f"Total rows: {len(ou_rows)}\n\n")
        f.write(f"Total errors: {len(errors)}\n")

        if errors:
            f.write("\nFirst errors:\n")
            for e in errors[:10]:
                f.write(f"- {e}\n")

try:

    with open("raw.txt", encoding="utf-8") as f:
        lines = [clean(l) for l in f if clean(l)]

    # ==========================================================
    # NEW FORMAT: ncaab_dk
    # ==========================================================
    if LEAGUE == "ncaab_dk":

        i = 0
        while i < len(lines):

            if lines[i].endswith("-logo"):
                i += 1
                continue

            if lines[i] in ("Spread", "Total", "Moneyline", "More Bets", "Today"):
                i += 1
                continue

            # detect team pattern: TeamA, at, TeamB
            if i + 2 < len(lines) and lines[i + 1] == "at":
                away = lines[i]
                home = lines[i + 2]

                # ignore numeric ranking lines before team
                if away.isdigit():
                    i += 1
                    continue

                games_seen += 1
                i += 3

                try:
                    # Spread (away)
                    spread_away = lines[i]
                    spread_away_odds = lines[i + 1]

                    # Over
                    over_marker = lines[i + 2]  # should be O
                    total_number = lines[i + 3]
                    over_odds = lines[i + 4]

                    # Moneyline away
                    ml_away = lines[i + 5]

                    # Spread (home)
                    spread_home = lines[i + 6]
                    spread_home_odds = lines[i + 7]

                    # Under
                    under_marker = lines[i + 8]  # should be U
                    total_number_2 = lines[i + 9]
                    under_odds = lines[i + 10]

                    # Moneyline home
                    ml_home = lines[i + 11]

                    # Time line
                    time_line = lines[i + 12]
                    if "Today" in time_line:
                        time_str = time_line.replace("Today", "").strip()
                    else:
                        time_str = ""

                    date_str = DATE.replace("_", "-")

                    # Moneyline rows
                    ml_rows.append([date_str, time_str, away, home, ml_away, "", "", "ncaab"])
                    ml_rows.append([date_str, time_str, home, away, ml_home, "", "", "ncaab"])

                    # Spread rows
                    sp_rows.append([date_str, time_str, away, home, spread_away, spread_away_odds, "", "", "ncaab"])
                    sp_rows.append([date_str, time_str, home, away, spread_home, spread_home_odds, "", "", "ncaab"])

                    # Totals rows (4 rows like original logic)
                    ou_rows.append([date_str, time_str, away, home, "O", total_number, over_odds, "", "", "ncaab"])
                    ou_rows.append([date_str, time_str, away, home, "U", total_number, under_odds, "", "", "ncaab"])
                    ou_rows.append([date_str, time_str, home, away, "O", total_number, over_odds, "", "", "ncaab"])
                    ou_rows.append([date_str, time_str, home, away, "U", total_number, under_odds, "", "", "ncaab"])

                    i += 13

                except Exception:
                    errors.append(f"Incomplete block for game: {away} @ {home}")
                    i += 1

            else:
                i += 1

    # ==========================================================
    # ORIGINAL FORMAT (UNCHANGED)
    # ==========================================================
    else:

        i = 0
        while i < len(lines):

            if "@" not in lines[i]:
                i += 1
                continue

            games_seen += 1

            try:
                away, home = [x.strip() for x in lines[i].split("@", 1)]
            except Exception:
                errors.append(f"Invalid game header format: {lines[i]}")
                i += 1
                continue

            if i + 1 >= len(lines):
                errors.append(f"Missing date/time for game: {away} @ {home}")
                break

            try:
                date_str, time_str = [x.strip() for x in lines[i + 1].split(",", 1)]
            except Exception:
                errors.append(f"Invalid date/time format after: {away} @ {home}")
                i += 2
                continue

            i += 2

            while i < len(lines) and lines[i] in ("Moneyline", "Spread", "Total", "Puck Line"):
                market = lines[i]
                normalized = "Spread" if market == "Puck Line" else market
                i += 1

                if lines[i:i + 3] != ["Odds", "% Handle", "% Bets"]:
                    errors.append(f"Malformed header in {market} for {away} @ {home}")
                    break

                i += 3

                if i + 7 >= len(lines):
                    errors.append(f"Incomplete market block for {away} @ {home}")
                    break

                a = lines[i:i + 4]
                b = lines[i + 4:i + 8]
                i += 8

                if normalized == "Moneyline":
                    t1, o1, h1, b1 = a
                    t2, o2, h2, b2 = b

                    opp1 = home if t1 == away else away
                    opp2 = home if t2 == away else away

                    ml_rows.append([date_str, time_str, t1, opp1, o1, h1.rstrip("%"), b1.rstrip("%"), LEAGUE])
                    ml_rows.append([date_str, time_str, t2, opp2, o2, h2.rstrip("%"), b2.rstrip("%"), LEAGUE])

                elif normalized == "Spread":
                    t1, o1, h1, b1 = a
                    t2, o2, h2, b2 = b

                    team1, spread1 = t1.rsplit(" ", 1)
                    team2, spread2 = t2.rsplit(" ", 1)

                    sp_rows.append([date_str, time_str, team1, team2, spread1, o1, h1.rstrip("%"), b1.rstrip("%"), f"{LEAGUE}_spreads"])
                    sp_rows.append([date_str, time_str, team2, team1, spread2, o2, h2.rstrip("%"), b2.rstrip("%"), f"{LEAGUE}_spreads"])

                elif normalized == "Total":
                    s1, o1, h1, b1 = a
                    s2, o2, h2, b2 = b

                    side1, total = s1.split(" ", 1)
                    side2, _ = s2.split(" ", 1)

                    ou_rows.append([date_str, time_str, away, home, side1, total, o1, h1.rstrip("%"), b1.rstrip("%"), f"{LEAGUE}_totals"])
                    ou_rows.append([date_str, time_str, away, home, side2, total, o2, h2.rstrip("%"), b2.rstrip("%"), f"{LEAGUE}_totals"])
                    ou_rows.append([date_str, time_str, home, away, side1, total, o1, h1.rstrip("%"), b1.rstrip("%"), f"{LEAGUE}_totals"])
                    ou_rows.append([date_str, time_str, home, away, side2, total, o2, h2.rstrip("%"), b2.rstrip("%"), f"{LEAGUE}_totals"])

    # ==========================================================
    # WRITE OUTPUT FILES
    # ==========================================================

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

    write_summary()

    if errors:
        raise RuntimeError("Parsing completed with errors")

except Exception as e:
    errors.append(str(e))
    write_summary()
    raise
