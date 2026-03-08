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

LOG_FILE = ERROR_DIR / "select_bets_audit.txt"


def f(x):
    try:
        return float(x)
    except:
        return 0.0


def audit(stage, status, msg="", df=None):

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a", encoding="utf-8") as fh:

        fh.write(f"\n[{ts}] [{stage}] {status}\n")

        if msg:
            fh.write(f"  MSG: {msg}\n")

        if df is not None and isinstance(df, pd.DataFrame):
            fh.write(
                f"  STATS: {len(df)} rows | {len(df.columns)} cols\n"
            )
            fh.write(
                f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n"
            )

        fh.write("-" * 40 + "\n")


###############################################################
######################## NBA RULES ############################
###############################################################

def get_moneyline(row, side):
    if side == "home":
        return f(row.get("home_moneyline") or row.get("home_juice_odds"))
    else:
        return f(row.get("away_moneyline") or row.get("away_juice_odds"))


def allow_nba_moneyline(row):

    home_edge = f(row.get("home_edge_decimal"))
    away_edge = f(row.get("away_edge_decimal"))

    home_ml = get_moneyline(row, "home")
    away_ml = get_moneyline(row, "away")

    if home_edge > 0.07 and -180 <= home_ml <= 180:
        return True

    if away_edge > 0.07 and -180 <= away_ml <= 180:
        return True

    return False


def allow_nba_spread(row):

    spread = f(row.get("line"))

    home_edge = f(row.get("home_edge_decimal"))
    away_edge = f(row.get("away_edge_decimal"))
    edge = max(home_edge, away_edge)

    if edge < 0.07:
        return False

    if abs(spread) > 15:
        return False

    if -2 <= spread <= 2:
        return False

    return True


def allow_nba_total(row):

    total = f(row.get("line"))
    proj = f(row.get("total_projected_points"))

    diff = abs(proj - total)

    home_spread = abs(f(row.get("home_spread")))
    away_spread = abs(f(row.get("away_spread")))
    spread = max(home_spread, away_spread)

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    if total > 245:
        return False

    if diff < 3:
        return False

    if spread >= 13 and total >= 240:
        return False

    if under_edge > over_edge:

        if total <= 205:
            return False

        if under_edge < 0.06:
            return False

        if under_edge > 0.40:
            return False

        return True

    else:

        if total <= 205:
            if over_edge < 0.04:
                return False
        else:
            if over_edge < 0.06:
                return False

        if over_edge > 0.35:
            return False

        return True


###############################################################
######################## NCAAB RULES ##########################
###############################################################

def allow_ncaab_moneyline(row):

    home_ml = f(row.get("home_moneyline"))
    away_ml = f(row.get("away_moneyline"))

    if home_ml <= -215:
        return False

    if away_ml < 0:
        return True

    return False


def allow_ncaab_spread(row):

    spread = f(row.get("line"))

    if 1 <= spread <= 3:
        return False

    if -10 <= spread <= -5:
        return False

    if 1 <= abs(spread) <= 7 and spread > 0:
        return False

    return True


###############################################################
################ NCAAB TOTAL UPDATED RULES ####################
###############################################################

def allow_ncaab_total(row):

    total = f(row.get("line"))
    bet_side = str(row.get("bet_side", "")).lower()

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    ###############################################################
    # OVER FILTER (ONLY IF BET SIDE IS OVER)
    ###############################################################

    if bet_side == "over":

        if (
            145 <= total <= 155
            and 0.12 <= over_edge <= 0.18
        ):
            return True

        return False

    ###############################################################
    # UNDER FILTER (ONLY IF BET SIDE IS UNDER)
    ###############################################################

    if bet_side == "under":

        if (
            141 <= total <= 150
            and 0.10 <= under_edge <= 0.22
        ):
            return True

        return False

    return False


###############################################################
#################### EDGE SELECTION ENGINE ####################
###############################################################

def process_file(csv_file):

    df = pd.read_csv(csv_file)

    if df.empty:
        return

    fname = csv_file.name.lower()

    league = "NBA" if "nba" in fname else "NCAAB"

    filtered_rows = []

    for _, row in df.iterrows():

        market_type = row.get("market_type")

        allowed = True

        if league == "NBA":

            if market_type == "moneyline":
                allowed = allow_nba_moneyline(row)

            elif market_type == "spread":
                allowed = allow_nba_spread(row)

            elif market_type == "total":
                allowed = allow_nba_total(row)

        else:

            if market_type == "moneyline":
                allowed = allow_ncaab_moneyline(row)

            elif market_type == "spread":
                allowed = allow_ncaab_spread(row)

            elif market_type == "total":
                allowed = allow_ncaab_total(row)

        if allowed:
            filtered_rows.append(row)

    if not filtered_rows:
        return

    out_df = pd.DataFrame(filtered_rows)

    out_path = OUTPUT_DIR / csv_file.name

    out_df.to_csv(out_path, index=False)

    print(f"Selected {len(out_df)} rows -> {out_path.name}")


###############################################################
############################ MAIN #############################
###############################################################

def main():

    files = list(INPUT_DIR.glob("*.csv"))

    if not files:
        audit("SELECT", "INFO", "No input files")
        return

    for f in files:

        try:
            process_file(f)

        except Exception as e:
            audit("SELECT", "ERROR", f"{f.name} failed: {e}")

    audit("SELECT", "SUCCESS", "Selection complete")


if __name__ == "__main__":
    main()
