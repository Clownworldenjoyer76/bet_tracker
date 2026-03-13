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

    if away_ml > 225:
        return False, "FAIL STEP 1 NBA ML | away extreme underdog", "", ""

    if home_ml > 225:
        return False, "FAIL STEP 1 NBA ML | home extreme underdog", "", ""

    if home_edge < 0.00001 and away_edge < 0.00001:
        return False, "FAIL STEP 1 NBA ML | edge too low", "", ""

    if home_edge > away_edge:
        return True, "PASS STEP 1 NBA ML | home stronger edge", "home", home_ml

    if away_edge > home_edge:
        return True, "PASS STEP 1 NBA ML | away stronger edge", "away", away_ml

    return False, "FAIL STEP 1 NBA ML | no edge advantage", "", ""


###############################################################
##################### STEP 2 NBA SPREAD #######################
###############################################################

def step2_nba_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))
    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    if home_edge >= away_edge:
        side, line, edge, opp_edge = "home", home_line, home_edge, away_edge
    else:
        side, line, edge, opp_edge = "away", away_line, away_edge, home_edge

    # FILTER: Away spread dead zone based on historical data
    if side == "away" and 10.0 <= line <= 13.9:
        return False, f"FAIL STEP 2 NBA SPREAD | away dead zone ({line})", "", ""

    if edge < 0.001:
        return False, "FAIL STEP 2 NBA SPREAD | edge too low", "", ""

    if edge <= opp_edge:
        return False, "FAIL STEP 2 NBA SPREAD | edge separation", "", ""

    return True, "PASS STEP 2 NBA SPREAD", side, line


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
    proj_diff = proj - line

    if line > 255:
        return False, "FAIL STEP 3 NBA TOTAL | extreme total", ""
    if max_spread >= 18 and line >= 240:
        return False, "FAIL STEP 3 NBA TOTAL | blowout risk", ""
    if abs(proj_diff) < 3:
        return False, "FAIL STEP 3 NBA TOTAL | projection diff", ""

    edge_threshold = 0.010 if line <= 235 else 0.020
    over_pass = over_edge >= edge_threshold and proj > line
    under_pass = under_edge >= edge_threshold and proj < line

    if over_pass and not under_pass:
        return True, "PASS STEP 3 NBA TOTAL | over edge", "over"
    if under_pass and not over_pass:
        return True, "PASS STEP 3 NBA TOTAL | under edge", "under"
    if over_pass and under_pass:
        if over_edge >= under_edge + 0.01:
            return True, "PASS STEP 3 NBA TOTAL | stronger over edge", "over"
        if under_edge >= over_edge + 0.01:
            return True, "PASS STEP 3 NBA TOTAL | stronger under edge", "under"
        return False, "FAIL STEP 3 NBA TOTAL | edges too close", ""

    return False, "FAIL STEP 3 NBA TOTAL | edge filter", ""


###############################################################
################### STEP 4 NCAAB MONEYLINE ####################
###############################################################

def step4_ncaab_moneyline(row):

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))
    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    if away_edge > home_edge:
        side, ml, edge, opp_edge = "away", away_ml, away_edge, home_edge
    else:
        side, ml, edge, opp_edge = "home", home_ml, home_edge, home_edge

    if ml > 150:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | extreme dog", "", ""
    if ml < -300:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | extreme favorite", "", ""
    if edge < 0.00001:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | edge too low", "", ""
    if edge <= opp_edge:
        return False, "FAIL STEP 4 NCAAB MONEYLINE | edge separation", "", ""

    return True, "PASS STEP 4 NCAAB MONEYLINE", side, ml


###############################################################
#################### STEP 5 NCAAB SPREAD ######################
###############################################################

def step5_ncaab_spread(row):

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))
    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    if home_edge >= away_edge:
        side, line, edge, opp_edge = "home", home_line, home_edge, away_edge
    else:
        side, line, edge, opp_edge = "away", away_line, away_edge, home_edge

    if edge > 0.9 or edge < 0.001:
        return False, "FAIL STEP 5 NCAAB SPREAD | edge threshold", "", ""
    if edge <= opp_edge:
        return False, "FAIL STEP 5 NCAAB SPREAD | edge separation", "", ""

    return True, "PASS STEP 5 NCAAB SPREAD", side, line


###############################################################
#################### STEP 6 NCAAB TOTAL #######################
###############################################################

def step6_ncaab_total(row):

    line = f(row.get("total"))
    proj = f(row.get("total_projected_points"))
    over_edge = f(row.get("over_edge_decimal"))
    proj_diff = abs(proj - line)

    if line < 150 or line > 200:
        return False, "FAIL STEP 6 NCAAB TOTAL | range", ""
    if proj_diff < 3:
        return False, "FAIL STEP 6 NCAAB TOTAL | projection diff", ""
    if 0.02 <= over_edge <= 0.50:
        return True, "PASS STEP 6 NCAAB TOTAL | over edge", "over"

    return False, "FAIL STEP 6 NCAAB TOTAL | edge filter", ""


###############################################################
######################## FILE PROCESSOR #######################
###############################################################

def process_file(csv_file):
    df = pd.read_csv(csv_file)
    if df.empty:
        report_line(f"FILE {csv_file.name} | INFO | empty input file")
        return

    league = "NBA" if "nba" in csv_file.name.lower() else "NCAAB"
    market_type = detect_market_from_filename(csv_file.name)

    if not market_type:
        report_line(f"FILE {csv_file.name} | ERROR | could not detect market type")
        return

    selected_rows = []
    for _, row in df.iterrows():
        label = game_label(row)
        if league == "NBA":
            if market_type == "moneyline":
                allowed, reason, bet_side, line = step1_nba_moneyline(row)
            elif market_type == "spread":
                allowed, reason, bet_side, line = step2_nba_spread(row)
            else:
                allowed, reason, bet_side = step3_nba_total(row)
                line = f(row.get("total"))
        else:
            if market_type == "moneyline":
                allowed, reason, bet_side, line = step4_ncaab_moneyline(row)
            elif market_type == "spread":
                allowed, reason, bet_side, line = step5_ncaab_spread(row)
            else:
                allowed, reason, bet_side = step6_ncaab_total(row)
                line = f(row.get("total"))

        if allowed:
            row_dict = row.to_dict()
            row_dict.update({"market_type": market_type, "bet_side": bet_side, "line": line})
            selected_rows.append(row_dict)
            report_line(f"PASS | {league} | {market_type} | {label} | {reason}")
        else:
            report_line(f"FAIL | {league} | {market_type} | {label} | {reason}")

    if selected_rows:
        out_df = pd.DataFrame(selected_rows)
        out_df.to_csv(OUTPUT_DIR / csv_file.name, index=False)
        print(f"Selected {len(out_df)} rows -> {csv_file.name}")


def main():
    reset_report()
    clear_previous_outputs()
    for fpath in sorted(INPUT_DIR.glob("*.csv")):
        try:
            process_file(fpath)
        except Exception as e:
            report_line(f"FILE {fpath.name} | ERROR | {e}")
    report_line("MAIN | selection rebuild complete")

if __name__ == "__main__":
    main()
