# scripts/dk_text_to_csv.py

## Parses raw DraftKings text into structured moneyline, spread, and totals CSV files
## for the given league and current date, and always writes a detailed summary/error log
## describing games detected, rows written, and any parsing issues.

#!/usr/bin/env python3

import csv
import sys
import os
import re
from datetime import datetime

LEAGUE = sys.argv[1] if len(sys.argv) > 1 else "ncaab"
DATE = datetime.now().strftime("%Y_%m_%d")
CURRENT_YEAR = datetime.now().year

OUT_DIR = "docs/win/manual/first"
ERROR_DIR = "docs/win/errors/dk_input"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)

# Preserve legacy filenames (no _dk in filename)
FILE_LEAGUE = LEAGUE.replace("_dk", "") if LEAGUE.endswith("_dk") else LEAGUE

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

def parse_month_date_line(line):
    """
    Example:
    Thu Feb 19th 7:00 PM
    Returns: (YYYY-MM-DD, "7:00 PM")
    """
    try:
        parts = line.split()
        month = parts[1]
        day = re.sub(r"(st|nd|rd|th)", "", parts[2])
        time_str = f"{parts[3]} {parts[4]}"

        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
        }

        month_num = month_map.get(month, "01")
        date_str = f"{CURRENT_YEAR}-{month_num}-{int(day):02d}"
        return date_str, time_str
    except Exception:
        return DATE.replace("_", "-"), ""

# ==========================================================
# MAIN
# ==========================================================

try:

    with open("raw.txt", encoding="utf-8") as f:
        lines = [clean(l) for l in f if clean(l)]

    # ======================================================
    # DK FORMAT BRANCH (ncaab_dk / nba_dk)
    # ======================================================
    if LEAGUE in ("ncaab_dk", "nba_dk"):

        output_league = FILE_LEAGUE  # write as nba or ncaab

        i = 0
        while i < len(lines):

            if lines[i].endswith("-logo") or lines[i] in (
                "Spread", "Total", "Moneyline", "More Bets"
            ):
                i += 1
                continue

            # detect team pattern
            if i + 2 < len(lines) and lines[i + 1] == "at":
                away = lines[i]
                home = lines[i + 2]

                if away.isdigit():
                    i += 1
                    continue

                games_seen += 1
                i += 3

                try:
                    spread_away = lines[i]
                    spread_away_odds = lines[i + 1]

                    total_marker = lines[i + 2]  # O
                    total_number = lines[i + 3]
                    over_odds = lines[i + 4]

                    ml_away = lines[i + 5]

                    spread_home = lines[i + 6]
                    spread_home_odds = lines[i + 7]

                    total_marker2 = lines[i + 8]  # U
                    total_number2 = lines[i + 9]
                    under_odds = lines[i + 10]

                    ml_home = lines[i + 11]

                    date_line = lines[i + 12]

                    if LEAGUE == "nba_dk":
                        date_str, time_str = parse_month_date_line(date_line)
                    else:
                        # ncaab_dk uses system date and strips Today
                        date_str = DATE.replace("_", "-")
                        time_str = date_line.replace("Today", "").strip()

                    # Moneyline
                    ml_rows.append([date_str, time_str, away, home, ml_away, "", "", output_league])
                    ml_rows.append([date_str, time_str, home, away, ml_home, "", "", output_league])

                    # Spread
                    sp_rows.append([date_str, time_str, away, home, spread_away, spread_away_odds, "", "", output_league])
                    sp_rows.append([date_str, time_str, home, away, spread_home, spread_home_odds, "", "", output_league])

                    # Totals (4 rows like legacy)
                    ou_rows.append([date_str, time_str, away, home, "O", total_number, over_odds, "", "", output_league])
                    ou_rows.append([date_str, time_str, away, home, "U", total_number, under_odds, "", "", output_league])
                    ou_rows.append([date_str, time_str, home, away, "O", total_number, over_odds, "", "", output_league])
                    ou_rows.append([date_str, time_str, home, away, "U", total_number, under_odds, "", "", output_league])

                    i += 13

                except Exception:
                    errors.append(f"Incomplete block for game: {away} @ {home}")
                    i += 1
            else:
                i += 1

    # ======================================================
    # LEGACY PARSER (UNCHANGED)
    # ======================================================
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

    # ======================================================
    # WRITE OUTPUT
    # ======================================================

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
