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

###############################################################
##################### STEP 1 NBA MONEYLINE ####################
###############################################################

def step1_nba_moneyline(row):

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    # allow almost all realistic ML prices
    if home_edge > 0.01 and -1000 <= home_ml <= 1000:
        return True, "PASS STEP 1 NBA MONEYLINE", "home", home_ml

    if away_edge > 0.01 and -1000 <= away_ml <= 1000:
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
        return True, "PASS STEP 2 NBA SPREAD", "home", home_line

    if away_edge >= 0.07 and -14.6 <= away_line <= 14.6 and not (-2 <= away_line <= 2):
        return True, "PASS STEP 2 NBA SPREAD", "away", away_line

    return False, "FAIL STEP 2 NBA SPREAD", "", ""


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
        return True, "PASS STEP 3 NBA TOTAL | both edges", "over" if over_edge >= under_edge else "under"

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

def blocked_ncaab_spread_line(line):
    if 1 <= line <= 3:
        return True
    if -10 <= line <= -5:
        return True
    if 1 <= abs(line) <= 7 and line > 0:
        return True
    return False


def step5_ncaab_spread(row):
    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    if blocked_ncaab_spread_line(home_line) or blocked_ncaab_spread_line(away_line):
        return False, "FAIL STEP 5 NCAAB SPREAD", "", ""

    if home_edge <= 0 and away_edge <= 0:
        return False, "FAIL STEP 5 NCAAB SPREAD | no positive spread edge", "", ""

    if home_edge >= away_edge:
        return True, "PASS STEP 5 NCAAB SPREAD", "home", home_line

    return True, "PASS STEP 5 NCAAB SPREAD", "away", away_line


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
        return False, "FAIL STEP 6 NCAAB TOTAL | range", ""

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
        report_line(f"FILE {csv_file.name} | ERROR | could not detect market type from filename")
        return

    report_line(f"FILE {csv_file.name} | START | league={league} | market_type={market_type} | rows={len(df)}")

    selected_rows = []
    pass_count = 0
    fail_count = 0
    out_path = OUTPUT_DIR / csv_file.name

    for _, row in df.iterrows():
        label = game_label(row)
        bet_side = ""
        line = ""

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
            row_dict["market_type"] = market_type
            row_dict["bet_side"] = bet_side
            row_dict["line"] = line
            selected_rows.append(row_dict)

            pass_count += 1
            report_line(f"PASS | {league} | {market_type} | {label} | {reason} | bet_side={bet_side} | line={line}")
        else:
            fail_count += 1
            report_line(f"FAIL | {league} | {market_type} | {label} | {reason}")

    if selected_rows:
        out_df = pd.DataFrame(selected_rows)
        out_df.to_csv(out_path, index=False)
        report_line(
            f"FILE {csv_file.name} | DONE | selected_rows={len(out_df)} | passed={pass_count} | failed={fail_count} | output={out_path}"
        )
        print(f"Selected {len(out_df)} rows -> {out_path.name}")
    else:
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        report_line(
            f"FILE {csv_file.name} | DONE | selected_rows=0 | passed={pass_count} | failed={fail_count} | no output file written"
        )
        print(f"Selected 0 rows -> {csv_file.name}")


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
