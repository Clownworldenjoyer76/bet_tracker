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

def is_american_odds(s: str) -> bool:
    return re.fullmatch(r"[+-]\d+", s or "") is not None

def is_spread(s: str) -> bool:
    return re.fullmatch(r"[+-]\d+(\.\d+)?", s or "") is not None

def is_total_number(s: str) -> bool:
    return re.fullmatch(r"\d+(\.\d+)?", s or "") is not None

def parse_time_line(line: str) -> str:
    m = re.search(r"(\d{1,2}:\d{2}\s?(AM|PM))", line)
    return m.group(1) if m else ""

def is_game_boundary(lines, idx: int) -> bool:
    # Detect start of next game by: team line followed by 'at'
    if idx + 1 >= len(lines):
        return False
    return lines[idx + 1].lower() == "at"

def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        if rows:
            w.writerows(rows)

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

def looks_like_noise_token(s: str) -> bool:
    # Tokens that often appear in the DK copy/paste and should not be treated as odds contexts
    if not s:
        return True
    low = s.lower()
    return low in {
        "today", "tomorrow", "spread", "total", "totals", "moneyline", "more bets", "at"
    }

def can_be_moneyline_token(lines, idx: int) -> bool:
    """
    Moneyline in your raw looks like a standalone American odds value inserted after totals,
    e.g. after 'O total odds' comes '-575' (away ML), and after 'U total odds' comes '+425' (home ML).
    This helper says whether lines[idx] can be treated as that standalone ML token.
    """
    if idx < 0 or idx >= len(lines):
        return False
    token = lines[idx]
    if not is_american_odds(token):
        return False

    # Exclude if next boundary starts a new game immediately
    if is_game_boundary(lines, idx):
        return False

    # Exclude if it’s obviously followed by a spread/total marker (then it's part of next market)
    if idx + 1 < len(lines):
        nxt = lines[idx + 1]
        if nxt in ("O", "U"):
            return False
        if is_spread(nxt):
            return False
        if parse_time_line(nxt):
            return False
        if looks_like_noise_token(nxt):
            # "More Bets", "Today 6:30 PM" etc. handled above via time; keep conservative
            pass

    return True

# ======================
# MAIN
# ======================

try:
    with open("raw.txt", encoding="utf-8") as f:
        lines = [clean(l) for l in f if clean(l)]

    # =========================
    # LEGACY (UNCHANGED)
    # =========================
    if not IS_DK:
        raise RuntimeError("Legacy logic preserved — use original branch")

    # =========================
    # DK PARSER
    # =========================

    i = 0
    while i < len(lines):

        # Detect away @ home structure
        if lines[i].lower() == "at" and i > 0 and i + 1 < len(lines):

            away = lines[i - 1]
            home = lines[i + 1]

            # Skip ranking lines
            if away.isdigit():
                i += 1
                continue

            games_seen += 1

            j = i + 2
            spread_away = spread_home = None
            spread_away_odds = spread_home_odds = None
            total_number = None
            total_over_odds = total_under_odds = None
            ml_away = ml_home = None
            game_time = ""

            while j < len(lines):

                # Proper boundary detection
                if is_game_boundary(lines, j):
                    break

                # Spread detection
                if is_spread(lines[j]) and j + 1 < len(lines) and is_american_odds(lines[j + 1]):
                    if spread_away is None:
                        spread_away = lines[j]
                        spread_away_odds = lines[j + 1]
                    else:
                        spread_home = lines[j]
                        spread_home_odds = lines[j + 1]
                    j += 2
                    continue

                # Totals detection (+ inline moneyline capture from your raw format)
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

                        # --- KEY FIX: capture standalone moneyline token that appears right after totals odds ---
                        # Your raw format commonly does:
                        #   O, total, odds, <AWAY_ML>, spread, odds, U, total, odds, <HOME_ML>, time...
                        if j < len(lines) and can_be_moneyline_token(lines, j):
                            if side == "O" and ml_away is None:
                                ml_away = lines[j]
                                j += 1
                            elif side == "U" and ml_home is None:
                                ml_home = lines[j]
                                j += 1

                        continue

                # Time
                t = parse_time_line(lines[j])
                if t:
                    game_time = t

                j += 1

            # =========================
            # WRITE (FORCED LEGACY DIRECTION)
            # =========================

            if spread_away and spread_home:
                sp_rows.append([
                    DATE.replace("_", "-"),
                    game_time,
                    away,
                    home,
                    spread_away,
                    spread_away_odds,
                    "",
                    "",
                    OUTPUT_LEAGUE
                ])
                sp_rows.append([
                    DATE.replace("_", "-"),
                    game_time,
                    home,
                    away,
                    spread_home,
                    spread_home_odds,
                    "",
                    "",
                    OUTPUT_LEAGUE
                ])

            if ml_away and ml_home:
                ml_rows.append([
                    DATE.replace("_", "-"),
                    game_time,
                    away,
                    home,
                    ml_away,
                    "",
                    "",
                    OUTPUT_LEAGUE
                ])
                ml_rows.append([
                    DATE.replace("_", "-"),
                    game_time,
                    home,
                    away,
                    ml_home,
                    "",
                    "",
                    OUTPUT_LEAGUE
                ])

            if total_number and total_over_odds and total_under_odds:
                for team1, team2 in [(away, home), (home, away)]:
                    ou_rows.append([
                        DATE.replace("_", "-"),
                        game_time,
                        team1,
                        team2,
                        "Over",
                        total_number,
                        total_over_odds,
                        "",
                        "",
                        OUTPUT_LEAGUE
                    ])
                    ou_rows.append([
                        DATE.replace("_", "-"),
                        game_time,
                        team1,
                        team2,
                        "Under",
                        total_number,
                        total_under_odds,
                        "",
                        "",
                        OUTPUT_LEAGUE
                    ])

            i = j
        else:
            i += 1

    # ======================
    # WRITE FILES (HEADERS GUARANTEED)
    # ======================

    write_csv(
        OUT_ML,
        ["date","time","team","opponent","odds","handle_pct","bets_pct","league"],
        ml_rows
    )

    write_csv(
        OUT_SP,
        ["date","time","team","opponent","spread","odds","handle_pct","bets_pct","league"],
        sp_rows
    )

    write_csv(
        OUT_OU,
        ["date","time","team","opponent","side","total","odds","handle_pct","bets_pct","league"],
        ou_rows
    )

    write_summary()

except Exception as e:
    errors.append(str(e))
    write_summary()
    raise
