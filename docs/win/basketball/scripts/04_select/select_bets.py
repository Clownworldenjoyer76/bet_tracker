#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
import re

###############################################################
######################## PATH CONFIG ##########################
###############################################################

INPUT_DIR = Path("docs/win/basketball/03_edges/ev_kelly")
SELECT_DIR = Path("docs/win/basketball/04_select")
DAILY_DIR = SELECT_DIR / "daily_slate"

SELECT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)

###############################################################
######################## BAND HELPER ##########################
###############################################################

def in_bands(value, bands):
    for low, high in bands:
        if low <= value <= high:
            return True
    return False

###############################################################
######################## NBA PARAMETERS #######################
###############################################################

# ---------- NBA MONEYLINE ----------

NBA_ML_HOME_ODDS_BANDS = [(-110,120)]
NBA_ML_HOME_EDGE_BANDS = [(-1,1)]
NBA_ALLOW_HOME_ML = True

NBA_ML_AWAY_ODDS_BANDS = [(-110,120)]
NBA_ML_AWAY_EDGE_BANDS = [(-1,1)]
NBA_ALLOW_AWAY_ML = True

# ---------- NBA SPREAD ----------

NBA_SPREAD_HOME_BANDS = [
(-99,7.4),
(10.1,99)
]

NBA_SPREAD_HOME_EDGE_BANDS = [
(-1,0.0199),
(0.10,999)
]

NBA_ALLOW_HOME_SPREAD = True

NBA_SPREAD_AWAY_BANDS = [
(-99,7.4),
(10.1,14.9)
]

NBA_SPREAD_AWAY_EDGE_BANDS = [
(-1,0.03),
(0.10,999)
]

NBA_ALLOW_AWAY_SPREAD = True

# ---------- NBA TOTAL ----------

NBA_TOTAL_OVER_BANDS = [(220,400)]
NBA_TOTAL_OVER_EDGE_BANDS = [(-1,1)]
NBA_ALLOW_OVER = True

NBA_TOTAL_UNDER_BANDS = [(0,400)]
NBA_TOTAL_UNDER_EDGE_BANDS = [(-1,1)]
NBA_ALLOW_UNDER = True

###############################################################
######################## NCAAB PARAMETERS #####################
###############################################################

# ---------- NCAAB MONEYLINE ----------

NCAAB_ML_HOME_ODDS_BANDS = [(-110,120)]
NCAAB_ML_HOME_EDGE_BANDS = [(-1,1)]
NCAAB_ALLOW_HOME_ML = True

NCAAB_ML_AWAY_ODDS_BANDS = [(-110,120)]
NCAAB_ML_AWAY_EDGE_BANDS = [(-1,1)]
NCAAB_ALLOW_AWAY_ML = True

# ---------- NCAAB SPREAD ----------

NCAAB_SPREAD_HOME_BANDS = [(-40,40)]
NCAAB_SPREAD_HOME_EDGE_BANDS = [(-1,1)]
NCAAB_ALLOW_HOME_SPREAD = True

NCAAB_SPREAD_AWAY_BANDS = [(-40,40)]
NCAAB_SPREAD_AWAY_EDGE_BANDS = [(-1,1)]
NCAAB_ALLOW_AWAY_SPREAD = True

# ---------- NCAAB TOTAL ----------

NCAAB_TOTAL_OVER_BANDS = [(0,400)]
NCAAB_TOTAL_OVER_EDGE_BANDS = [(-1,1)]
NCAAB_ALLOW_OVER = True

NCAAB_TOTAL_UNDER_BANDS = [(0,400)]
NCAAB_TOTAL_UNDER_EDGE_BANDS = [(-1,1)]
NCAAB_ALLOW_UNDER = True

###############################################################
######################## HELPERS ##############################
###############################################################

def f(x):
    try:
        if pd.isna(x):
            return 0
        return float(x)
    except:
        return 0


def detect_market(filename):

    name = filename.lower()

    if "moneyline" in name or "_ml" in name:
        return "moneyline"

    if "spread" in name:
        return "spread"

    if "total" in name:
        return "total"

    return ""


def extract_date(filename):

    m = re.search(r"\d{4}_\d{2}_\d{2}", filename)

    if m:
        return m.group(0)

    return None

###############################################################
######################## MONEYLINE ############################
###############################################################

def moneyline(row, league):

    home_ml=f(row.get("home_dk_moneyline_american"))
    away_ml=f(row.get("away_dk_moneyline_american"))

    home_edge=f(row.get("home_ml_edge_decimal"))
    away_edge=f(row.get("away_ml_edge_decimal"))

    if league=="NBA":

        if NBA_ALLOW_HOME_ML and in_bands(home_ml,NBA_ML_HOME_ODDS_BANDS) and in_bands(home_edge,NBA_ML_HOME_EDGE_BANDS):
            if home_edge>=away_edge:
                return True,"home",home_ml,home_edge

        if NBA_ALLOW_AWAY_ML and in_bands(away_ml,NBA_ML_AWAY_ODDS_BANDS) and in_bands(away_edge,NBA_ML_AWAY_EDGE_BANDS):
            if away_edge>home_edge:
                return True,"away",away_ml,away_edge

    else:

        if NCAAB_ALLOW_HOME_ML and in_bands(home_ml,NCAAB_ML_HOME_ODDS_BANDS) and in_bands(home_edge,NCAAB_ML_HOME_EDGE_BANDS):
            if home_edge>=away_edge:
                return True,"home",home_ml,home_edge

        if NCAAB_ALLOW_AWAY_ML and in_bands(away_ml,NCAAB_ML_AWAY_ODDS_BANDS) and in_bands(away_edge,NCAAB_ML_AWAY_EDGE_BANDS):
            if away_edge>home_edge:
                return True,"away",away_ml,away_edge

    return False,"","",0

###############################################################
######################## SPREAD ###############################
###############################################################

def spread(row, league):

    home_line=f(row.get("home_spread"))
    away_line=f(row.get("away_spread"))

    home_edge=f(row.get("home_spread_edge_decimal"))
    away_edge=f(row.get("away_spread_edge_decimal"))

    if league=="NBA":

        home_valid = (
            NBA_ALLOW_HOME_SPREAD
            and in_bands(home_line, NBA_SPREAD_HOME_BANDS)
            and in_bands(home_edge, NBA_SPREAD_HOME_EDGE_BANDS)
        )

        away_valid = (
            NBA_ALLOW_AWAY_SPREAD
            and in_bands(away_line, NBA_SPREAD_AWAY_BANDS)
            and in_bands(away_edge, NBA_SPREAD_AWAY_EDGE_BANDS)
        )

    else:

        home_valid = (
            NCAAB_ALLOW_HOME_SPREAD
            and in_bands(home_line, NCAAB_SPREAD_HOME_BANDS)
            and in_bands(home_edge, NCAAB_SPREAD_HOME_EDGE_BANDS)
        )

        away_valid = (
            NCAAB_ALLOW_AWAY_SPREAD
            and in_bands(away_line, NCAAB_SPREAD_AWAY_BANDS)
            and in_bands(away_edge, NCAAB_SPREAD_AWAY_EDGE_BANDS)
        )

    if home_valid and away_valid:
        if home_edge >= away_edge:
            return True,"home",home_line,home_edge
        else:
            return True,"away",away_line,away_edge

    if home_valid:
        return True,"home",home_line,home_edge

    if away_valid:
        return True,"away",away_line,away_edge

    return False,"","",0

###############################################################
######################## TOTAL ################################
###############################################################

def total(row, league):

    line=f(row.get("total"))

    over_edge=f(row.get("over_edge_decimal"))
    under_edge=f(row.get("under_edge_decimal"))

    if over_edge>=under_edge:
        side="over"; edge=over_edge
    else:
        side="under"; edge=under_edge

    if league=="NBA":

        if side=="over" and NBA_ALLOW_OVER:
            if in_bands(line,NBA_TOTAL_OVER_BANDS) and in_bands(edge,NBA_TOTAL_OVER_EDGE_BANDS):
                return True,"over",line,edge

        if side=="under" and NBA_ALLOW_UNDER:
            if in_bands(line,NBA_TOTAL_UNDER_BANDS) and in_bands(edge,NBA_TOTAL_UNDER_EDGE_BANDS):
                return True,"under",line,edge

    else:

        if side=="over" and NCAAB_ALLOW_OVER:
            if in_bands(line,NCAAB_TOTAL_OVER_BANDS) and in_bands(edge,NCAAB_TOTAL_OVER_EDGE_BANDS):
                return True,"over",line,edge

        if side=="under" and NCAAB_ALLOW_UNDER:
            if in_bands(line,NCAAB_TOTAL_UNDER_BANDS) and in_bands(edge,NCAAB_TOTAL_UNDER_EDGE_BANDS):
                return True,"under",line,edge

    return False,"","",0

###############################################################
######################## PROCESS FILE #########################
###############################################################

def process_file(file):

    df=pd.read_csv(file)

    if df.empty:
        return None

    league="NBA" if "nba" in file.name.lower() else "NCAAB"
    market=detect_market(file.name)

    rows=[]

    for _,row in df.iterrows():

        if market=="moneyline":
            ok,side,line,edge=moneyline(row,league)

        elif market=="spread":
            ok,side,line,edge=spread(row,league)

        else:
            ok,side,line,edge=total(row,league)

        if ok:

            r=row.to_dict()

            r["bet_side"]=side
            r["line"]=line
            r["market_type"]=market
            r["market"]=league

            rows.append(r)

    if rows:
        return pd.DataFrame(rows)

    return None

###############################################################
######################## MAIN #################################
###############################################################

def main():

    dfs=[]
    detected_date=None

    for file in sorted(INPUT_DIR.glob("*.csv")):

        if detected_date is None:
            detected_date=extract_date(file.name)

        df=process_file(file)

        if df is not None:
            dfs.append(df)

    if not dfs:
        print("No bets selected")
        return

    df=pd.concat(dfs,ignore_index=True)

    nba=df[df["market"]=="NBA"]
    ncaab=df[df["market"]=="NCAAB"]

    if detected_date is None:
        detected_date="unknown_date"

    nba_file=DAILY_DIR/f"{detected_date}_nba.csv"
    ncaab_file=DAILY_DIR/f"{detected_date}_ncaab.csv"

    nba.to_csv(nba_file,index=False)
    ncaab.to_csv(ncaab_file,index=False)

    print("NBA bets:",len(nba))
    print("NCAAB bets:",len(ncaab))


if __name__=="__main__":
    main()
