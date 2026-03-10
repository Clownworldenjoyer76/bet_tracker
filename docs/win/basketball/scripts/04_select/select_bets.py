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


###############################################################
################ CLEAN OUTPUTS (SAFE RESET) ###################
###############################################################

def clear_previous_outputs():
    removed = 0
    for fpath in OUTPUT_DIR.glob("*.csv"):
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

    # AWAY STRATEGY: Data shows 4-0 record in 0.05-0.15 edge band
    if 0.05 < away_edge <= 0.15:
        # Success found in favorites and short underdogs
        if away_ml <= 274:
            return True, "PASS STEP 1 NBA ML | away sweet spot", "away", away_ml

    # HOME STRATEGY: Data shows 0% win rate on big home dogs (>0.30 edge is 0-7)
    # Target favorites where you have a small, realistic edge
    if home_ml < 0 and 0.00 <= home_edge <= 0.05:
        return True, "PASS STEP 1 NBA ML | home favorite value", "home", home_ml

    return False, "FAIL STEP 1 NBA ML | out of performance bands", "", ""

###############################################################
##################### STEP 2 NBA SPREAD #######################
###############################################################

def step2_nba_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    # Baseline edge requirement
    edge_threshold = 0.020 
    
    # ADVANTAGE: Home Favorites (home_line is negative)
    # Give a slight edge boost to home favorites between -3 and -7
    is_home_fav = home_line <= -3 and home_line >= -7
    if is_home_fav:
        effective_home_threshold = 0.015  # Easier to pass for strong home spots
    else:
        effective_home_threshold = edge_threshold

    # RISK MITIGATION: Large Road Underdogs (away_line is high positive)
    # Require a larger edge for road teams getting 10+ points
    if away_line >= 10:
        effective_away_threshold = 0.035
    else:
        effective_away_threshold = edge_threshold

    # Evaluation logic
    if home_edge >= effective_home_threshold or away_edge >= effective_away_threshold:

        # If both pass, pick the one with the highest relative edge
        if home_edge >= away_edge:
            return True, "PASS STEP 2 NBA SPREAD | home advantage", "home", home_line

        return True, "PASS STEP 2 NBA SPREAD | away edge", "away", away_line

    return False, "FAIL STEP 2 NBA SPREAD | edge below threshold", "", ""


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

    # REVISED: Increased limit to 260 to capture high-scoring matchups
    if line > 260:
        return False, "FAIL STEP 3 NBA TOTAL | extreme total", ""

    # REVISED: Reduced minimum disagreement from 1.0 to 0.1 to allow more plays
    if proj_diff < 0.1:
        return False, "FAIL STEP 3 NBA TOTAL | projection diff", ""

    # REVISED: Increased blowout threshold from 16 to 20
    if max_spread >= 20 and line >= 240:
        return False, "FAIL STEP 3 NBA TOTAL | blowout filter", ""

    # REVISED: Lowered edge requirement to 0.005 (half a percent)
    edge_threshold = 0.005

    over_pass = over_edge >= edge_threshold
    under_pass = under_edge >= edge_threshold

    if over_pass or under_pass:
        if over_edge >= under_edge:
            return True, "PASS STEP 3 NBA TOTAL | over edge", "over"
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

    home_prob = f(row.get("home_ml_prob"))
    away_prob = f(row.get("away_ml_prob"))

    ###########################################################
    # Select side with stronger edge
    ###########################################################

    if away_edge > home_edge:
        side = "away"
        ml = away_ml
        edge = away_edge
        prob = away_prob
        opp_edge = home_edge
    else:
        side = "home"
        ml = home_ml
        edge = home_edge
        prob = home_prob
        opp_edge = away_edge

    ###########################################################
    # LONGSHOT FILTER
    ###########################################################

    if ml > 200:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | longshot filter", "", ""

    ###########################################################
    # HEAVY FAVORITE FILTER
    ###########################################################

    if ml < -185:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | heavy favorite filter", "", ""

    ###########################################################
    # EDGE + PROBABILITY REQUIREMENTS
    ###########################################################

    # Underdogs
    if ml >= 100:

        if edge < 0.02:
            return False, "FAIL STEP 4 NCAAB MONEYLINE | dog edge too low", "", ""

        if prob < 0.42:
            return False, "FAIL STEP 4 NCAAB MONEYLINE | dog prob too low", "", ""

    # Favorites
    else:

        if edge < 0.015:
            return False, "FAIL STEP 4 NCAAB MONEYLINE | favorite edge too low", "", ""

        if prob < 0.53:
            return False, "FAIL STEP 4 NCAAB MONEYLINE | favorite prob too low", "", ""

    ###########################################################
    # EDGE SEPARATION (MODEL CONVICTION)
    ###########################################################

    if edge - opp_edge < 0.005:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | edge separation too small", "", ""

    ###########################################################
    # PASS
    ###########################################################

    return True, "PASS STEP 4 NCAAB MONEYLINE", side, ml


###############################################################
#################### STEP 5 NCAAB SPREAD ######################
###############################################################

def step5_ncaab_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    home_prob = f(row.get("home_spread_prob"))
    away_prob = f(row.get("away_spread_prob"))

    ###########################################################
    # Select side with stronger edge
    ###########################################################

    if home_edge >= away_edge:
        side = "home"
        line = home_line
        edge = home_edge
        prob = home_prob
        opp_edge = away_edge
    else:
        side = "away"
        line = away_line
        edge = away_edge
        prob = away_prob
        opp_edge = home_edge

    ###########################################################
    # Tiny spread filter (avoid efficient pick'em zone)
    ###########################################################

    if abs(line) < 1.5:
        return False, "FAIL STEP 5 NCAAB SPREAD | tiny spread", "", ""

    ###########################################################
    # Extreme spread filter (garbage-time volatility)
    ###########################################################

    if abs(line) > 17:
        return False, "FAIL STEP 5 NCAAB SPREAD | extreme spread", "", ""

    ###########################################################
    # Minimum edge requirement
    ###########################################################

    if edge < 0.015:
        return False, "FAIL STEP 5 NCAAB SPREAD | edge too low", "", ""

    ###########################################################
    # Probability confirmation
    ###########################################################

    if prob < 0.4:
        return False, "FAIL STEP 5 NCAAB SPREAD | probability too low", "", ""

    ###########################################################
    # Model conviction (edge separation)
    ###########################################################

    if edge - opp_edge < 0.005:
        return False, "FAIL STEP 5 NCAAB SPREAD | edge separation too small", "", ""

    ###########################################################
    # PASS
    ###########################################################

    return True, "PASS STEP 5 NCAAB SPREAD", side, line


###############################################################
#################### STEP 6 NCAAB TOTAL #######################
###############################################################

def step6_ncaab_total_final(row):
    line = f(row.get("total"))
    proj = f(row.get("total_projected_points"))
    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))
    
    proj_diff = abs(proj - line)

    # ---------------------------------------------------------
    # 1. THE "DYNAMITE" OVER LOGIC (Success Zone: 150+)
    # ---------------------------------------------------------
    if over_edge > under_edge:
        # Band A: Under 150 (High-Bar)
        if line < 150 and over_edge >= 0.40 and proj_diff >= 4:
            return True, "PASS NCAAB | high conviction over", "over"
        
        # Band B: Over 150 (Value Zone)
        if line >= 150 and over_edge >= 0.05 and proj_diff >= 2:
            return True, "PASS NCAAB | over 150 value zone", "over"

    # ---------------------------------------------------------
    # 2. THE "CAREFUL" UNDER LOGIC (Success Zone: < 145)
    # ---------------------------------------------------------
    elif under_edge > over_edge:
        # Avoid high totals for Unders (Too much variance)
        if line > 145:
            return False, "FAIL NCAAB UNDER | total too high for under", ""

        # Higher entry requirements for Unders to protect ROI
        if under_edge >= 0.08 and proj_diff >= 4:
            return True, "PASS NCAAB | careful under spot", "under"

    return False, "FAIL NCAAB | no edge/range match", ""

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
