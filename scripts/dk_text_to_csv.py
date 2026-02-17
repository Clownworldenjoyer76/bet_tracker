# scripts/dk_text_to_csv.py

#!/usr/bin/env python3

import csv
import sys
import os
import re
from datetime import datetime

LEAGUE_INPUT = sys.argv[1] if len(sys.argv) > 1 else "ncaab"
DATE = datetime.now().strftime("%Y_%m_%d")

IS_DK = LEAGUE_INPUT.endswith("_dk")
BASE_LEAGUE = LEAGUE_INPUT.replace("_dk", "")
OUTPUT_LEAGUE = BASE_LEAGUE

OUT_DIR = "docs/win/manual/first"
ERROR_DIR = "docs/win/errors/dk_input"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)

OUT_ML = f"{OUT_DIR}/dk_{BASE_LEAGUE}_moneyline_{DATE}.csv"
OUT_SP = f"{OUT_DIR}/dk_{BASE_LEAGUE}_spreads_{DATE}.csv"
OUT_OU = f"{OUT_DIR}/dk_{BASE_LEAGUE}_totals_{DATE}.csv"

ERROR_LOG = f"{ERROR_DIR}/dk_input_{DATE}.txt"

ml_rows, sp_rows, ou_rows = [], [], []
games_seen = 0
errors = []

# ======================
# HELPERS
# ======================

def clean(line: str) -> str:
    return (
        line.replace("opens in a new tab", "")
            .replace("−", "-")
            .replace("-logo", "")
            .strip()
    )

def is_american_odds(s):
    return re.fullmatch(r"[+-]\d+", s or "") is not None

def is_spread(s):
    return re.fullmatch(r"[+-]\d+(\.\d+)?", s or "") is not None

def is_total_number(s):
    return re.fullmatch(r"\d+(\.\d+)?", s or "") is not None

def parse_time(line):
    m = re.search(r"(\d{1,2}:\d{2}\s?(AM|PM))", line)
    return m.group(1) if m else ""

def write_summary():
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("DK INPUT PARSE SUMMARY\n")
        f.write("======================\n\n")
        f.write(f"League Input: {LEAGUE_INPUT}\n")
        f.write(f"League Output: {OUTPUT_LEAGUE}\n")
        f.write(f"Date: {DATE}\n")
        f.write(f"Games detected: {games_seen}\n")
        f.write(f"Moneyline rows: {len(ml_rows)}\n")
        f.write(f"Spread rows: {len(sp_rows)}\n")
        f.write(f"Total rows: {len(ou_rows)}\n\n")
        f.write(f"Total errors: {len(errors)}\n")

# ======================
# MAIN
# ======================

try:

    with open("raw.txt", encoding="utf-8") as f:
        lines = [clean(l) for l in f if clean(l)]

    if not IS_DK:
        raise RuntimeError("Legacy logic unchanged")

    i = 0
    while i < len(lines):

        # Detect game start by literal "at"
        if lines[i].lower() == "at" and i > 0 and i + 1 < len(lines):

            away = lines[i - 1]
            home = lines[i + 1]

            # Skip ranking-only lines
            if away.isdigit():
                i += 1
                continue

            games_seen += 1
            j = i + 2

            spread_vals = []
            spread_odds = []
            total_number = None
            total_over_odds = None
            total_under_odds = None
            moneylines = []
            game_time = ""

            while j < len(lines):

                # Stop at next game
                if lines[j].lower() == "at":
                    break

                # Spread detection
                if is_spread(lines[j]) and j + 1 < len(lines) and is_american_odds(lines[j + 1]):
                    spread_vals.append(lines[j])
                    spread_odds.append(lines[j + 1])
                    j += 2
                    continue

                # Total detection
                if lines[j] in ("O", "U") and j + 2 < len(lines):
                    side = lines[j]
                    total = lines[j + 1]
                    odds = lines[j + 2]

                    if is_total_number(total) and is_american_odds(odds):
                        total_number = total
                        if side == "O":
                            total_over_odds = odds
                        else:
                            total_under_odds = odds
                        j += 3
                        continue

                # Moneyline detection
                if is_american_odds(lines[j]):
                    moneylines.append(lines[j])
                    j += 1
                    continue

                # Time detection
                t = parse_time(lines[j])
                if t:
                    game_time = t

                j += 1

            # ---- WRITE OUTPUT ----

            date_fmt = DATE.replace("_", "-")

            # Spread
            if len(spread_vals) >= 2 and len(spread_odds) >= 2:
                sp_rows.append([
                    date_fmt, game_time, away, home,
                    spread_vals[0], spread_odds[0],
                    "", "", OUTPUT_LEAGUE
                ])
                sp_rows.append([
                    date_fmt, game_time, home, away,
                    spread_vals[1], spread_odds[1],
                    "", "", OUTPUT_LEAGUE
                ])

            # Moneyline (use last two American odds in block)
            if len(moneylines) >= 2:
                ml_rows.append([
                    date_fmt, game_time, away, home,
                    moneylines[-2], "", "", OUTPUT_LEAGUE
                ])
                ml_rows.append([
                    date_fmt, game_time, home, away,
                    moneylines[-1], "", "", OUTPUT_LEAGUE
                ])

            # Totals
            if total_number and total_over_odds and total_under_odds:
                for team1, team2 in [(away, home), (home, away)]:
                    ou_rows.append([
                        date_fmt, game_time, team1, team2,
                        "Over", total_number,
                        total_over_odds, "", "", OUTPUT_LEAGUE
                    ])
                    ou_rows.append([
                        date_fmt, game_time, team1, team2,
                        "Under", total_number,
                        total_under_odds, "", "", OUTPUT_LEAGUE
                    ])

            i = j
        else:
            i += 1

    # ======================
    # WRITE FILES
    # ======================

    if ml_rows:
        with open(OUT_ML, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date","time","team","opponent","odds","handle_pct","bets_pct","league"])
            w.writerows(ml_rows)

    if sp_rows:
        with open(OUT_SP, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date","time","team","opponent","spread","odds","handle_pct","bets_pct","league"])
            w.writerows(sp_rows)

    if ou_rows:
        with open(OUT_OU, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date","time","team","opponent","side","total","odds","handle_pct","bets_pct","league"])
            w.writerows(ou_rows)

    write_summary()

except Exception as e:
    errors.append(str(e))
    write_summary()
    raise
