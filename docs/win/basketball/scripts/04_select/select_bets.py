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
        return float(x)
    except:
        return 0.0


def log(msg):

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(REPORT_FILE, "a", encoding="utf-8") as fh:
        fh.write(f"[{ts}] {msg}\n")


def get_moneyline(row, side):

    if side == "home":
        return f(row.get("home_dk_moneyline_american"))
    else:
        return f(row.get("away_dk_moneyline_american"))


###############################################################
##################### STEP 1 NBA MONEYLINE ####################
###############################################################

def step1_nba_moneyline(row):

    home_edge = f(row.get("home_edge_decimal"))
    away_edge = f(row.get("away_edge_decimal"))

    home_ml = get_moneyline(row, "home")
    away_ml = get_moneyline(row, "away")

    cond1_home = home_edge > 0.07
    cond2_home = -180 <= home_ml <= 180

    cond1_away = away_edge > 0.07
    cond2_away = -180 <= away_ml <= 180

    if cond1_home and cond2_home:
        return True, "PASS: HOME meets edge + odds"

    if cond1_away and cond2_away:
        return True, "PASS: AWAY meets edge + odds"

    return False, "FAIL: Moneyline conditions not met"


###############################################################
##################### STEP 2 NBA SPREAD #######################
###############################################################

def step2_nba_spread(row):

    home_edge = f(row.get("home_edge_decimal"))
    away_edge = f(row.get("away_edge_decimal"))

    spread = f(row.get("line"))

    edge_ok = home_edge >= 0.07 or away_edge >= 0.07

    if not edge_ok:
        return False, "FAIL: Spread edge below threshold"

    if -2 <= spread <= 2:
        return False, "FAIL: Spread inside dead zone (-2 to 2)"

    if abs(spread) > 14.6:
        return False, "FAIL: Spread outside ±14.6"

    return True, "PASS: Spread rules satisfied"


###############################################################
##################### STEP 3 NBA TOTAL ########################
###############################################################

def step3_nba_total(row):

    line = f(row.get("line"))
    proj = f(row.get("total_projected_points"))

    home_spread = abs(f(row.get("home_spread")))
    away_spread = abs(f(row.get("away_spread")))

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    diff = abs(proj - line)

    if line > 245:
        return False, "FAIL: Total exceeds 245"

    if diff < 3:
        return False, "FAIL: Projection diff < 3"

    if max(home_spread, away_spread) >= 13 and line >= 240:
        return False, "FAIL: Blowout filter triggered"

    ###########################################################
    # UNDER LOGIC
    ###########################################################

    if under_edge > over_edge:

        if line <= 205:
            return False, "FAIL: Under requires line > 205"

        if not (0.06 <= under_edge <= 0.40):
            return False, "FAIL: Under edge outside range"

        return True, "PASS: NBA UNDER"

    ###########################################################
    # OVER LOGIC
    ###########################################################

    else:

        if line <= 205:

            if over_edge < 0.04:
                return False, "FAIL: Over edge < 0.04"

        else:

            if over_edge < 0.06:
                return False, "FAIL: Over edge < 0.06"

        if over_edge > 0.35:
            return False, "FAIL: Over edge > 0.35"

        return True, "PASS: NBA OVER"


###############################################################
#################### STEP 4 NCAAB MONEYLINE ###################
###############################################################

def step4_ncaab_moneyline(row):

    home_ml = get_moneyline(row, "home")
    away_ml = get_moneyline(row, "away")

    if away_ml < 0:
        return True, "PASS: Away favorite"

    if home_ml > -215:
        return True, "PASS: Home price acceptable"

    return False, "FAIL: NCAAB ML rules"


###############################################################
#################### STEP 5 NCAAB SPREAD ######################
###############################################################

def step5_ncaab_spread(row):

    line = f(row.get("line"))

    if 1 <= line <= 3:
        return False, "FAIL: Spread 1–3 blocked"

    if -10 <= line <= -5:
        return False, "FAIL: Spread -10 to -5 blocked"

    if 1 <= abs(line) <= 7 and line > 0:
        return False, "FAIL: Positive spread 1–7 blocked"

    return True, "PASS: NCAAB spread allowed"


###############################################################
#################### STEP 6 NCAAB TOTAL #######################
###############################################################

def step6_ncaab_total(row):

    line = f(row.get("line"))

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    ###########################################################
    # OVER SIDE
    ###########################################################

    if 145 <= line <= 155 and 0.12 <= over_edge <= 0.18:
        return True, "PASS: NCAAB OVER"

    ###########################################################
    # UNDER SIDE
    ###########################################################

    if 141 <= line <= 150 and 0.10 <= under_edge <= 0.22:
        return True, "PASS: NCAAB UNDER"

    return False, "FAIL: NCAAB total rules"


###############################################################
######################## ENGINE ###############################
###############################################################

def process_file(file):

    df = pd.read_csv(file)

    if df.empty:
        return

    fname = file.name.lower()

    league = "NBA" if "nba" in fname else "NCAAB"

    results = []

    for _, row in df.iterrows():

        market = str(row.get("market_type")).lower()

        if league == "NBA":

            if market == "moneyline":
                passed, reason = step1_nba_moneyline(row)

            elif market == "spread":
                passed, reason = step2_nba_spread(row)

            elif market == "total":
                passed, reason = step3_nba_total(row)

            else:
                continue

        else:

            if market == "moneyline":
                passed, reason = step4_ncaab_moneyline(row)

            elif market == "spread":
                passed, reason = step5_ncaab_spread(row)

            elif market == "total":
                passed, reason = step6_ncaab_total(row)

            else:
                continue

        game = f"{row.get('away_team')} @ {row.get('home_team')}"

        if passed:

            results.append(row)

            log(f"PASS | {league} | {market} | {game} | {reason}")

        else:

            log(f"FAIL | {league} | {market} | {game} | {reason}")

    if results:

        out_df = pd.DataFrame(results)

        out_path = OUTPUT_DIR / file.name

        out_df.to_csv(out_path, index=False)

        print(f"{file.name} -> {len(out_df)} selections")


###############################################################
############################ MAIN #############################
###############################################################

def main():

    files = list(INPUT_DIR.glob("*.csv"))

    if not files:
        log("No input files found")
        return

    for f in files:

        try:

            process_file(f)

        except Exception as e:

            log(f"ERROR processing {f.name}: {e}")

    log("Selection run complete")


if __name__ == "__main__":
    main()
