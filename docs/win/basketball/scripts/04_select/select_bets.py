#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime

###############################################################
######################## PATH CONFIG ##########################
###############################################################

INPUT_DIR = Path("docs/win/basketball/03_edges/ev_kelly")
SELECT_DIR = Path("docs/win/basketball/04_select")
DAILY_DIR = SELECT_DIR / "daily_slate"
TOTALS_DIR = DAILY_DIR / "totals"
ERROR_DIR = Path("docs/win/basketball/errors/04_select")

SELECT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_DIR.mkdir(parents=True, exist_ok=True)
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
    with open(REPORT_FILE, "w") as fh:
        fh.write("BASKETBALL SELECT REPORT\n")
        fh.write("="*80+"\n")

def report_line(text):
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(REPORT_FILE,"a") as fh:
        fh.write(f"[{ts}] {text}\n")

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
###################### NBA MONEYLINE ##########################
###############################################################

def nba_moneyline(row):

    home_edge=f(row.get("home_ml_edge_decimal"))
    away_edge=f(row.get("away_ml_edge_decimal"))

    home_ml=f(row.get("home_dk_moneyline_american"))
    away_ml=f(row.get("away_dk_moneyline_american"))

    home_valid=-1000<=home_ml<=-140
    away_valid=-1000<=away_ml<=-140

    if not home_valid and not away_valid:
        return False,"",""

    if home_edge<0.0000001 and away_edge<0.0000001:
        return False,"",""

    if home_valid and home_edge>away_edge:
        return True,"home",home_ml

    if away_valid and away_edge>home_edge:
        return True,"away",away_ml

    return False,"",""

###############################################################
###################### NBA SPREAD #############################
###############################################################

def nba_spread(row):

    home_line=f(row.get("home_spread"))
    away_line=f(row.get("away_spread"))

    home_edge=f(row.get("home_spread_edge_decimal"))
    away_edge=f(row.get("away_spread_edge_decimal"))

    if home_edge>=away_edge:
        side="home"; line=home_line; edge=home_edge; opp=away_edge
    else:
        side="away"; line=away_line; edge=away_edge; opp=home_edge

    if side=="away" and 10<=line<=13.9:
        return False,"",""

    if edge<0.0000001:
        return False,"",""

    if edge<=opp:
        return False,"",""

    return True,side,line

###############################################################
###################### NBA TOTAL ##############################
###############################################################

def nba_total(row):

    line=f(row.get("total"))
    proj=f(row.get("total_projected_points"))

    over_edge=f(row.get("over_edge_decimal"))
    under_edge=f(row.get("under_edge_decimal"))

    diff=proj-line

    if abs(diff)<3:
        return False,"",""

    if over_edge>under_edge and over_edge>0.01:
        return True,"over",line

    if under_edge>over_edge and under_edge>0.01:
        return True,"under",line

    return False,"",""

###############################################################
##################### NCAAB MONEYLINE #########################
###############################################################

def ncaab_moneyline(row):

    home_ml=f(row.get("home_dk_moneyline_american"))
    away_ml=f(row.get("away_dk_moneyline_american"))

    home_edge=f(row.get("home_ml_edge_decimal"))
    away_edge=f(row.get("away_ml_edge_decimal"))

    if away_edge>home_edge:
        side="away"; ml=away_ml; edge=away_edge; opp=home_edge
    else:
        side="home"; ml=home_ml; edge=home_edge; opp=away_edge

    if ml>150 or ml<-300:
        return False,"",""

    if edge<0.00001:
        return False,"",""

    if edge<=opp:
        return False,"",""

    return True,side,ml

###############################################################
##################### NCAAB SPREAD ############################
###############################################################

def ncaab_spread(row):

    home_line=f(row.get("home_spread"))
    away_line=f(row.get("away_spread"))

    home_edge=f(row.get("home_spread_edge_decimal"))
    away_edge=f(row.get("away_spread_edge_decimal"))

    if home_edge>=away_edge:
        side="home"; line=home_line; edge=home_edge; opp=away_edge
    else:
        side="away"; line=away_line; edge=away_edge; opp=home_edge

    if edge<0.001:
        return False,"",""

    if edge<=opp:
        return False,"",""

    return True,side,line

###############################################################
##################### NCAAB TOTAL #############################
###############################################################

def ncaab_total(row):

    line=f(row.get("total"))
    proj=f(row.get("total_projected_points"))
    over_edge=f(row.get("over_edge_decimal"))

    if line<150 or line>200:
        return False,"",""

    if abs(proj-line)<3:
        return False,"",""

    if over_edge>0.02:
        return True,"over",line

    return False,"",""

###############################################################
###################### FILE PROCESSOR #########################
###############################################################

def process_file(csv_file):

    df=pd.read_csv(csv_file)

    if df.empty:
        return None

    league="NBA" if "nba" in csv_file.name.lower() else "NCAAB"
    market=detect_market(csv_file.name)

    rows=[]

    for _,row in df.iterrows():

        if league=="NBA":

            if market=="moneyline":
                ok,side,line=nba_moneyline(row)
            elif market=="spread":
                ok,side,line=nba_spread(row)
            else:
                ok,side,line=nba_total(row)

        else:

            if market=="moneyline":
                ok,side,line=ncaab_moneyline(row)
            elif market=="spread":
                ok,side,line=ncaab_spread(row)
            else:
                ok,side,line=ncaab_total(row)

        if ok:

            r=row.to_dict()
            r["bet_side"]=side
            r["line"]=line
            r["market_type"]=market
            rows.append(r)

    if rows:
        return pd.DataFrame(rows)

    return None

###############################################################
######################## MAIN PIPELINE ########################
###############################################################

def main():

    reset_report()

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

    nba_path=DAILY_DIR/"nba_selected.csv"
    ncaab_path=DAILY_DIR/"ncaab_selected.csv"

    nba.to_csv(nba_path,index=False)
    ncaab.to_csv(ncaab_path,index=False)

    print("NBA bets:",len(nba))
    print("NCAAB bets:",len(ncaab))

    # build history

    nba_hist=[pd.read_csv(f) for f in DAILY_DIR.glob("*_nba.csv")]
    if nba_hist:
        pd.concat(nba_hist).to_csv(TOTALS_DIR/"NBA_final.csv",index=False)

    ncaab_hist=[pd.read_csv(f) for f in DAILY_DIR.glob("*_ncaab.csv")]
    if ncaab_hist:
        pd.concat(ncaab_hist).to_csv(TOTALS_DIR/"NCAAB_final.csv",index=False)

if __name__=="__main__":
    main()
