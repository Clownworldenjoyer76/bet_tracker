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


def detect_league(row, filename):
    league = s(row.get("league")).lower()

    if league:
        return league

    name = filename.lower()
    if "nba" in name:
        return "nba"
    if "ncaab" in name:
        return "ncaab"

    return ""


###############################################################
################ CLEAN OUTPUTS (SAFE RESET) ###################
###############################################################

def clear_previous_outputs():
    removed = 0
    for fpath in OUTPUT_DIR.rglob("*.csv"):
        fpath.unlink(missing_ok=True)
        removed += 1
    report_line(f"MAIN | cleared old select files | removed={removed}")


###############################################################
##################### STEP 1 NBA MONEYLINE ####################
###############################################################

def step1_nba_moneyline(row):

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    if 0.05 < away_edge <= 0.15:
        if away_ml <= 274:
            return True, "PASS STEP 1 NBA ML | away sweet spot", "away", away_ml

    if home_ml < 0 and 0.00 <= home_edge <= 0.05:
        return True, "PASS STEP 1 NBA ML | home favorite value", "home", home_ml

    return False, "FAIL STEP 1 NBA ML | out of performance bands", "", 0


###############################################################
##################### STEP 2 NBA SPREAD #######################
###############################################################

def step2_nba_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    edge_threshold = 0.020

    is_home_fav = home_line <= -3 and home_line >= -7
    effective_home_threshold = 0.015 if is_home_fav else edge_threshold

    effective_away_threshold = 0.035 if away_line >= 10 else edge_threshold

    if home_edge >= effective_home_threshold or away_edge >= effective_away_threshold:

        if home_edge >= away_edge:
            return True, "PASS STEP 2 NBA SPREAD | home advantage", "home", home_line

        return True, "PASS STEP 2 NBA SPREAD | away edge", "away", away_line

    return False, "FAIL STEP 2 NBA SPREAD | edge below threshold", "", 0


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

    if line > 260:
        return False, "FAIL STEP 3 NBA TOTAL | extreme total", "", 0

    if proj_diff < 0.1:
        return False, "FAIL STEP 3 NBA TOTAL | projection diff", "", 0

    if max_spread >= 20 and line >= 240:
        return False, "FAIL STEP 3 NBA TOTAL | blowout filter", "", 0

    edge_threshold = 0.005

    over_pass = over_edge >= edge_threshold
    under_pass = under_edge >= edge_threshold

    if over_pass or under_pass:
        if over_edge >= under_edge:
            return True, "PASS STEP 3 NBA TOTAL | over edge", "over", line
        return True, "PASS STEP 3 NBA TOTAL | under edge", "under", line

    return False, "FAIL STEP 3 NBA TOTAL | edge filter", "", 0


###############################################################
################### STEP 4 NCAAB MONEYLINE ####################
###############################################################

def step4_ncaab_moneyline(row):

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    home_prob = f(row.get("home_ml_prob"))
    away_prob = f(row.get("away_ml_prob"))

    if away_edge > home_edge:
        side, ml, edge, prob, opp_edge = "away", away_ml, away_edge, away_prob, home_edge
    else:
        side, ml, edge, prob, opp_edge = "home", home_ml, home_edge, home_prob, away_edge

    if ml > 200:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | longshot filter", "", 0

    if ml < -185:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | heavy favorite filter", "", 0

    if ml >= 100:
        if edge < 0.02 or prob < 0.42:
            return False, "FAIL STEP 4 NCAAB MONEYLINE | dog filters", "", 0
    else:
        if edge < 0.015 or prob < 0.53:
            return False, "FAIL STEP 4 NCAAB MONEYLINE | favorite filters", "", 0

    if edge - opp_edge < 0.005:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | edge separation too small", "", 0

    return True, "PASS STEP 4 NCAAB MONEYLINE", side, ml


###############################################################
############################ PROCESS ##########################
###############################################################

def process_file(fpath):

    market = detect_market_from_filename(fpath.name)

    df = pd.read_csv(fpath)

    selections = []

    for _, row in df.iterrows():

        league = detect_league(row, fpath.name)

        if league == "nba":

            if market == "moneyline":
                passed, reason, side, price = step1_nba_moneyline(row)

            elif market == "spread":
                passed, reason, side, price = step2_nba_spread(row)

            elif market == "total":
                passed, reason, side, price = step3_nba_total(row)

            else:
                continue

        elif league == "ncaab":

            if market == "moneyline":
                passed, reason, side, price = step4_ncaab_moneyline(row)

            elif market == "spread":
                passed, reason, side, price = step5_ncaab_spread(row)

            elif market == "total":
                passed, reason, side, price = step6_ncaab_total_final(row)

            else:
                continue

        else:
            report_line(f"{game_label(row)} | UNKNOWN LEAGUE")
            continue

        if passed:
            row_dict = row.to_dict()
            row_dict["bet_side"] = side
            row_dict["bet_price"] = price
            row_dict["selection_reason"] = reason
            selections.append(row_dict)

    if selections:

        out_df = pd.DataFrame(selections)

        out_file = OUTPUT_DIR / f"selected_{fpath.name}"

        out_df.to_csv(out_file, index=False)

        report_line(f"{fpath.name} | selections={len(out_df)}")

    else:
        report_line(f"{fpath.name} | no selections")


###############################################################
############################ MAIN #############################
###############################################################

def main():

    reset_report()

    clear_previous_outputs()

    files = sorted(INPUT_DIR.glob("*.csv"))

    for fpath in files:
        try:
            process_file(fpath)
        except Exception as e:
            report_line(f"FILE {fpath.name} | ERROR | {type(e).__name__}: {e}")

    report_line("MAIN | selection rebuild complete")


if __name__ == "__main__":
    main()
