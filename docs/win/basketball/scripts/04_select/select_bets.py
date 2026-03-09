#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = ERROR_DIR / "select_report.txt"


###############################################################
######################## HELPERS ##############################
###############################################################

def f(x):
    try:
        if pd.isna(x):
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def s(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def reset_report():
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("BASKETBALL 04_SELECT REPORT\n")
        fh.write("=" * 100 + "\n")


def report_line(text):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(REPORT_FILE, "a", encoding="utf-8") as fh:
        fh.write(f"[{ts}] {text}\n")


def game_label(row):
    away = s(row.get("away_team"))
    home = s(row.get("home_team"))
    game_id = s(row.get("game_id"))
    date = s(row.get("game_date"))
    return f"{date} | {away} @ {home} | game_id={game_id}"


def detect_market_from_filename(file_name):
    name = file_name.lower()
    if "moneyline" in name:
        return "moneyline"
    if "spread" in name:
        return "spread"
    if "total" in name:
        return "total"
    return ""


def blocked_ncaab_spread_line(line):
    if 1 <= line <= 3:
        return True
    if -10 <= line <= -5:
        return True
    if 1 <= abs(line) <= 7 and line > 0:
        return True
    return False


def clear_previous_outputs():
    removed = 0
    for fpath in OUTPUT_DIR.glob("*.csv"):
        fpath.unlink(missing_ok=True)
        removed += 1
    report_line(f"MAIN | INFO | Cleared previous select outputs | removed_files={removed}")


###############################################################
##################### STEP 1 NBA MONEYLINE ####################
###############################################################

def step1_nba_moneyline(row):

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    if home_edge > 0.07 and -180 <= home_ml <= 180:
        return True, "PASS STEP 1 NBA MONEYLINE", "home", home_ml

    if away_edge > 0.07 and -180 <= away_ml <= 180:
        return True, "PASS STEP 1 NBA MONEYLINE", "away", away_ml

    return False, "FAIL STEP 1 NBA MONEYLINE", "", ""


###############################################################
##################### STEP 2 NBA SPREAD #######################
###############################################################

def step2_nba_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    if home_edge >= 0.07 and -14.6 <= home_line <= 14.6 and not (-2 <= home_line <= 2):
        return True, "PASS STEP 2 NBA SPREAD"

    if away_edge >= 0.07 and -14.6 <= away_line <= 14.6 and not (-2 <= away_line <= 2):
        return True, "PASS STEP 2 NBA SPREAD"

    return False, "FAIL STEP 2 NBA SPREAD"


###############################################################
##################### STEP 3 NBA TOTAL ########################
###############################################################

def step3_nba_total(row):

    line = f(row.get("total"))
    proj = f(row.get("total_projected_points"))

    home_spread = abs(f(row.get("home_spread")))
    away_spread = abs(f(row.get("away_spread")))
    max_spread = max(home_spread, away_spread)

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    proj_diff = abs(proj - line)

    if line > 245:
        return False, "FAIL STEP 3 NBA TOTAL | total limit", ""

    if proj_diff < 5:
        return False, "FAIL STEP 3 NBA TOTAL | projection diff", ""

    if max_spread >= 13 and line >= 240:
        return False, "FAIL STEP 3 NBA TOTAL | blowout filter", ""

    over_pass = 0.10 <= over_edge <= 0.35
    under_pass = 0.10 <= under_edge <= 0.35

    if over_pass and under_pass:
        return True, "PASS STEP 3 NBA TOTAL | both edges valid", "over" if over_edge >= under_edge else "under"

    if over_pass:
        return True, "PASS STEP 3 NBA TOTAL | over edge", "over"

    if under_pass:
        return True, "PASS STEP 3 NBA TOTAL | under edge", "under"

    return False, "FAIL STEP 3 NBA TOTAL | edge filter", ""


###############################################################
################### STEP 4 NCAAB MONEYLINE ####################
###############################################################

def step4_ncaab_moneyline(row):

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    if away_ml > -150 and away_edge >= 0.08:
        return True, "PASS STEP 4 NCAAB MONEYLINE", "away", away_ml

    if home_ml > -200 and home_edge >= 0.05:
        return True, "PASS STEP 4 NCAAB MONEYLINE", "home", home_ml

    return False, "FAIL STEP 4 NCAAB MONEYLINE", "", ""


###############################################################
#################### STEP 5 NCAAB SPREAD ######################
###############################################################

def step5_ncaab_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    if blocked_ncaab_spread_line(home_line) or blocked_ncaab_spread_line(away_line):
        return False, "FAIL STEP 5 NCAAB SPREAD"

    return True, "PASS STEP 5 NCAAB SPREAD"


###############################################################
#################### STEP 6 NCAAB TOTAL #######################
###############################################################

def step6_ncaab_total(row):

    line = f(row.get("total"))
    proj = f(row.get("total_projected_points"))

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    proj_diff = abs(proj - line)

    if line < 130 or line > 175:
        return False, "FAIL STEP 6 NCAAB TOTAL | total range", ""

    if proj_diff < 6:
        return False, "FAIL STEP 6 NCAAB TOTAL | projection diff", ""

    over_pass = 0.10 <= over_edge <= 0.22
    under_pass = 0.12 <= under_edge <= 0.22

    if over_pass and under_pass:
        return True, "PASS STEP 6 NCAAB TOTAL | both edges", "over" if over_edge >= under_edge else "under"

    if over_pass:
        return True, "PASS STEP 6 NCAAB TOTAL | over edge", "over"

    if under_pass:
        return True, "PASS STEP 6 NCAAB TOTAL | under edge", "under"

    return False, "FAIL STEP 6 NCAAB TOTAL | edge filter", ""


###############################################################
############################ MAIN #############################
###############################################################

def main():

    reset_report()
    clear_previous_outputs()

    files = sorted(INPUT_DIR.glob("*.csv"))

    for fpath in files:
        process_file(fpath)

    report_line("MAIN | SUCCESS | Selection run complete")


if __name__ == "__main__":
    main()
