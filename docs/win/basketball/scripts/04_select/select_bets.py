#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path

###############################################################
######################## PATH CONFIG ##########################
###############################################################

INPUT_DIR = Path("docs/win/basketball/03_edges/ev_kelly")
SELECT_DIR = Path("docs/win/basketball/04_select")
DAILY_DIR = SELECT_DIR / "daily_slate"
TOTALS_DIR = DAILY_DIR / "totals"

SELECT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_DIR.mkdir(parents=True, exist_ok=True)

###############################################################
######################## NBA PARAMETERS #######################
###############################################################

# ---------- NBA MONEYLINE ----------
NBA_ML_HOME_ODDS_MIN = -2000
NBA_ML_HOME_ODDS_MAX = 500
NBA_ML_HOME_EDGE_MIN = -1
NBA_ML_HOME_EDGE_MAX = 1
NBA_ALLOW_HOME_ML = True

NBA_ML_AWAY_ODDS_MIN = -2000
NBA_ML_AWAY_ODDS_MAX = 500
NBA_ML_AWAY_EDGE_MIN = -1
NBA_ML_AWAY_EDGE_MAX = 1
NBA_ALLOW_AWAY_ML = True

# ---------- NBA SPREAD ----------
NBA_SPREAD_HOME_MIN = -40
NBA_SPREAD_HOME_MAX = 40
NBA_SPREAD_HOME_EDGE_MIN = -1
NBA_SPREAD_HOME_EDGE_MAX = 1
NBA_ALLOW_HOME_SPREAD = True

NBA_SPREAD_AWAY_MIN = -40
NBA_SPREAD_AWAY_MAX = 40
NBA_SPREAD_AWAY_EDGE_MIN = -1
NBA_SPREAD_AWAY_EDGE_MAX = 1
NBA_ALLOW_AWAY_SPREAD = True

# ---------- NBA TOTAL ----------
NBA_TOTAL_OVER_MIN = 0
NBA_TOTAL_OVER_MAX = 400
NBA_TOTAL_OVER_EDGE_MIN = -1
NBA_TOTAL_OVER_EDGE_MAX = 1
NBA_ALLOW_OVER = True

NBA_TOTAL_UNDER_MIN = 0
NBA_TOTAL_UNDER_MAX = 400
NBA_TOTAL_UNDER_EDGE_MIN = -1
NBA_TOTAL_UNDER_EDGE_MAX = 1
NBA_ALLOW_UNDER = True

###############################################################
######################## NCAAB PARAMETERS #####################
###############################################################

# ---------- NCAAB MONEYLINE ----------
NCAAB_ML_HOME_ODDS_MIN = -2000
NCAAB_ML_HOME_ODDS_MAX = 500
NCAAB_ML_HOME_EDGE_MIN = -1
NCAAB_ML_HOME_EDGE_MAX = 1
NCAAB_ALLOW_HOME_ML = True

NCAAB_ML_AWAY_ODDS_MIN = -2000
NCAAB_ML_AWAY_ODDS_MAX = 500
NCAAB_ML_AWAY_EDGE_MIN = -1
NCAAB_ML_AWAY_EDGE_MAX = 1
NCAAB_ALLOW_AWAY_ML = True

# ---------- NCAAB SPREAD ----------
NCAAB_SPREAD_HOME_MIN = -40
NCAAB_SPREAD_HOME_MAX = 40
NCAAB_SPREAD_HOME_EDGE_MIN = -1
NCAAB_SPREAD_HOME_EDGE_MAX = 1
NCAAB_ALLOW_HOME_SPREAD = True

NCAAB_SPREAD_AWAY_MIN = -40
NCAAB_SPREAD_AWAY_MAX = 40
NCAAB_SPREAD_AWAY_EDGE_MIN = -1
NCAAB_SPREAD_AWAY_EDGE_MAX = 1
NCAAB_ALLOW_AWAY_SPREAD = True

# ---------- NCAAB TOTAL ----------
NCAAB_TOTAL_OVER_MIN = 0
NCAAB_TOTAL_OVER_MAX = 400
NCAAB_TOTAL_OVER_EDGE_MIN = -1
NCAAB_TOTAL_OVER_EDGE_MAX = 1
NCAAB_ALLOW_OVER = True

NCAAB_TOTAL_UNDER_MIN = 0
NCAAB_TOTAL_UNDER_MAX = 400
NCAAB_TOTAL_UNDER_EDGE_MIN = -1
NCAAB_TOTAL_UNDER_EDGE_MAX = 1
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


def detect_market(file):
    name=file.lower()
    if "moneyline" in name:
        return "moneyline"
    if "spread" in name:
        return "spread"
    if "total" in name:
        return "total"
    return ""


###############################################################
######################## MONEYLINE ############################
###############################################################

def moneyline(row, league):

    home_ml=f(row.get("home_dk_moneyline_american"))
    away_ml=f(row.get("away_dk_moneyline_american"))

    home_edge=f(row.get("home_ml_edge_decimal"))
    away_edge=f(row.get("away_ml_edge_decimal"))

    if league=="NBA":

        if NBA_ALLOW_HOME_ML and NBA_ML_HOME_ODDS_MIN<=home_ml<=NBA_ML_HOME_ODDS_MAX and NBA_ML_HOME_EDGE_MIN<=home_edge<=NBA_ML_HOME_EDGE_MAX:
            if home_edge>=away_edge:
                return True,"home",home_ml,home_edge

        if NBA_ALLOW_AWAY_ML and NBA_ML_AWAY_ODDS_MIN<=away_ml<=NBA_ML_AWAY_ODDS_MAX and NBA_ML_AWAY_EDGE_MIN<=away_edge<=NBA_ML_AWAY_EDGE_MAX:
            if away_edge>home_edge:
                return True,"away",away_ml,away_edge

    else:

        if NCAAB_ALLOW_HOME_ML and NCAAB_ML_HOME_ODDS_MIN<=home_ml<=NCAAB_ML_HOME_ODDS_MAX and NCAAB_ML_HOME_EDGE_MIN<=home_edge<=NCAAB_ML_HOME_EDGE_MAX:
            if home_edge>=away_edge:
                return True,"home",home_ml,home_edge

        if NCAAB_ALLOW_AWAY_ML and NCAAB_ML_AWAY_ODDS_MIN<=away_ml<=NCAAB_ML_AWAY_ODDS_MAX and NCAAB_ML_AWAY_EDGE_MIN<=away_edge<=NCAAB_ML_AWAY_EDGE_MAX:
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

    if home_edge>=away_edge:
        side="home"; line=home_line; edge=home_edge
    else:
        side="away"; line=away_line; edge=away_edge

    if league=="NBA":

        if side=="home" and NBA_ALLOW_HOME_SPREAD:
            if NBA_SPREAD_HOME_MIN<=line<=NBA_SPREAD_HOME_MAX and NBA_SPREAD_HOME_EDGE_MIN<=edge<=NBA_SPREAD_HOME_EDGE_MAX:
                return True,"home",line,edge

        if side=="away" and NBA_ALLOW_AWAY_SPREAD:
            if NBA_SPREAD_AWAY_MIN<=line<=NBA_SPREAD_AWAY_MAX and NBA_SPREAD_AWAY_EDGE_MIN<=edge<=NBA_SPREAD_AWAY_EDGE_MAX:
                return True,"away",line,edge

    else:

        if side=="home" and NCAAB_ALLOW_HOME_SPREAD:
            if NCAAB_SPREAD_HOME_MIN<=line<=NCAAB_SPREAD_HOME_MAX and NCAAB_SPREAD_HOME_EDGE_MIN<=edge<=NCAAB_SPREAD_HOME_EDGE_MAX:
                return True,"home",line,edge

        if side=="away" and NCAAB_ALLOW_AWAY_SPREAD:
            if NCAAB_SPREAD_AWAY_MIN<=line<=NCAAB_SPREAD_AWAY_MAX and NCAAB_SPREAD_AWAY_EDGE_MIN<=edge<=NCAAB_SPREAD_AWAY_EDGE_MAX:
                return True,"away",line,edge

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
            if NBA_TOTAL_OVER_MIN<=line<=NBA_TOTAL_OVER_MAX and NBA_TOTAL_OVER_EDGE_MIN<=edge<=NBA_TOTAL_OVER_EDGE_MAX:
                return True,"over",line,edge

        if side=="under" and NBA_ALLOW_UNDER:
            if NBA_TOTAL_UNDER_MIN<=line<=NBA_TOTAL_UNDER_MAX and NBA_TOTAL_UNDER_EDGE_MIN<=edge<=NBA_TOTAL_UNDER_EDGE_MAX:
                return True,"under",line,edge

    else:

        if side=="over" and NCAAB_ALLOW_OVER:
            if NCAAB_TOTAL_OVER_MIN<=line<=NCAAB_TOTAL_OVER_MAX and NCAAB_TOTAL_OVER_EDGE_MIN<=edge<=NCAAB_TOTAL_OVER_EDGE_MAX:
                return True,"over",line,edge

        if side=="under" and NCAAB_ALLOW_UNDER:
            if NCAAB_TOTAL_UNDER_MIN<=line<=NCAAB_TOTAL_UNDER_MAX and NCAAB_TOTAL_UNDER_EDGE_MIN<=edge<=NCAAB_TOTAL_UNDER_EDGE_MAX:
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

            # DEBUG INFORMATION
            r["debug_league"]=league
            r["debug_market"]=market
            r["debug_selected_side"]=side
            r["debug_edge_value"]=edge
            r["debug_odds_value"]=f(row.get("home_dk_moneyline_american"))
            r["debug_line_value"]=line
            r["debug_projection_value"]=f(row.get("total_projected_points"))
            r["debug_pass_reason"]=f"{league} {market} {side} passed parameter filters"

            rows.append(r)

    if rows:
        return pd.DataFrame(rows)

    return None


###############################################################
######################## MAIN #################################
###############################################################

def main():

    dfs=[]

    for file in sorted(INPUT_DIR.glob("*.csv")):

        df=process_file(file)

        if df is not None:
            dfs.append(df)

    if not dfs:
        print("No bets selected")
        return

    df=pd.concat(dfs,ignore_index=True)

    nba=df[df["market"].str.upper()=="NBA"]
    ncaab=df[df["market"].str.upper()=="NCAAB"]

    nba.to_csv(DAILY_DIR/"nba_selected.csv",index=False)
    ncaab.to_csv(DAILY_DIR/"ncaab_selected.csv",index=False)

    print("NBA bets:",len(nba))
    print("NCAAB bets:",len(ncaab))


if __name__=="__main__":
    main()
