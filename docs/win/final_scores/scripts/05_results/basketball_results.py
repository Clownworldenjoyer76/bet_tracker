#!/usr/bin/env python3
# docs/win/basketball/scripts/05_results/basketball_results.py

import pandas as pd
import glob
import os
import re
from pathlib import Path
from datetime import datetime

###############################################################
######################## PATH CONFIG ##########################
###############################################################

BASE = Path("docs/win/basketball")

SELECT_DIR = BASE / "04_select/daily_slate"

NBA_SCORE_DIR = Path("docs/win/final_scores/results/nba/final_scores")
NCAAB_SCORE_DIR = Path("docs/win/final_scores/results/ncaab/final_scores")

NBA_OUTPUT = Path("docs/win/final_scores/results/nba/graded")
NCAAB_OUTPUT = Path("docs/win/final_scores/results/ncaab/graded")

DEEP_SUMMARY_DIR = Path("docs/win/final_scores/deeper_summaries")

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

EDGE_REPORT = ERROR_DIR / "basketball_edge_summary.txt"
LOG_FILE = ERROR_DIR / "basketball_results_log.txt"

###############################################################
######################## HELPERS ##############################
###############################################################

def log(msg):

    with open(LOG_FILE,"a") as f:

        f.write(f"[{datetime.now()}] {msg}\n")


def safe_read(path):

    try:

        if not Path(path).exists():
            return pd.DataFrame()

        df=pd.read_csv(path)

        if df is None or df.empty:
            return pd.DataFrame()

        return df

    except Exception as e:

        log(f"READ ERROR {path} {e}")
        return pd.DataFrame()


###############################################################
######################## OUTCOME LOGIC ########################
###############################################################

def determine_outcome(row):

    try:

        market=row.get("market_type","")
        side=row.get("bet_side","")

        away=float(row["away_score"])
        home=float(row["home_score"])

        # MONEYLINE
        if market=="moneyline":

            if away==home:
                return "Push"

            if side=="home":
                return "Win" if home>away else "Loss"

            if side=="away":
                return "Win" if away>home else "Loss"

        # SPREAD
        if market=="spread":

            line=float(row.get("line",0))

            if side=="home":
                diff=(home+line)-away
            else:
                diff=(away+line)-home

            if abs(diff)<1e-9:
                return "Push"

            return "Win" if diff>0 else "Loss"

        # TOTAL
        if market=="total":

            line=float(row.get("line",0))
            total=away+home

            if abs(total-line)<1e-9:
                return "Push"

            if side=="over":
                return "Win" if total>line else "Loss"

            if side=="under":
                return "Win" if total<line else "Loss"

    except Exception:
        pass

    return "Unknown"

###############################################################
######################## EDGE EXTRACTION ######################
###############################################################

def extract_edge(row):

    side=row.get("bet_side","")
    market=row.get("market_type","")

    if market=="moneyline":

        if side=="home":
            return row.get("home_ml_edge_decimal")

        if side=="away":
            return row.get("away_ml_edge_decimal")

    if market=="spread":

        if side=="home":
            return row.get("home_spread_edge_decimal")

        if side=="away":
            return row.get("away_spread_edge_decimal")

    if market=="total":

        if side=="over":
            return row.get("over_edge_decimal")

        if side=="under":
            return row.get("under_edge_decimal")

    return None

###############################################################
######################## GRADING ENGINE #######################
###############################################################

def grade_league(league):

    if league=="NBA":

        score_dir=NBA_SCORE_DIR
        output_dir=NBA_OUTPUT
        pattern="*_nba.csv"
        suffix="NBA"

    else:

        score_dir=NCAAB_SCORE_DIR
        output_dir=NCAAB_OUTPUT
        pattern="*_ncaab.csv"
        suffix="NCAAB"

    output_dir.mkdir(parents=True,exist_ok=True)

    bet_files=glob.glob(str(SELECT_DIR / pattern))

    dates=set()

    for f in bet_files:

        m=re.search(r"(\d{4}_\d{2}_\d{2})",f)

        if m:
            dates.add(m.group(1))

    for date in sorted(dates):

        score_file=score_dir / f"{date}_final_scores_{suffix}.csv"

        if not score_file.exists():
            continue

        bet_paths=glob.glob(str(SELECT_DIR / f"{date}{pattern[-8:]}"))

        dfs=[safe_read(x) for x in bet_paths]

        dfs=[d for d in dfs if not d.empty]

        if not dfs:
            continue

        bets=pd.concat(dfs)

        scores=safe_read(score_file)

        if scores.empty:
            continue

        df=pd.merge(

            bets,
            scores,
            on=["away_team","home_team","game_date"],
            validate="many_to_one"

        )

        df["bet_result"]=df.apply(determine_outcome,axis=1)

        outfile=output_dir / f"{date}_results_{suffix}.csv"

        df.to_csv(outfile,index=False)

        log(f"{league} graded {date} rows={len(df)}")

###############################################################
######################## MASTER BUILD #########################
###############################################################

def build_master(league):

    if league=="NBA":

        outdir=NBA_OUTPUT
        suffix="NBA"

    else:

        outdir=NCAAB_OUTPUT
        suffix="NCAAB"

    files=glob.glob(str(outdir / f"*_results_{suffix}.csv"))

    dfs=[safe_read(f) for f in files]

    dfs=[d for d in dfs if not d.empty]

    if not dfs:
        return

    df=pd.concat(dfs)

    master=outdir / f"{suffix}_final.csv"

    df.sort_values(["game_date","away_team","home_team"]).to_csv(master,index=False)

###############################################################
######################## EDGE REPORT ##########################
###############################################################

def build_edge_report():

    rows=[]

    for league,path in [

        ("NBA",NBA_OUTPUT/"NBA_final.csv"),
        ("NCAAB",NCAAB_OUTPUT/"NCAAB_final.csv")

    ]:

        df=safe_read(path)

        if df.empty:
            continue

        win_edges=[]
        loss_edges=[]

        for _,row in df.iterrows():

            edge=extract_edge(row)

            if edge is None:
                continue

            if row["bet_result"]=="Win":
                win_edges.append(edge)

            if row["bet_result"]=="Loss":
                loss_edges.append(edge)

        win_avg=sum(win_edges)/len(win_edges) if win_edges else 0
        loss_avg=sum(loss_edges)/len(loss_edges) if loss_edges else 0

        rows.append(f"\n{league}")
        rows.append(f"Win edge avg: {win_avg:.4f}")
        rows.append(f"Loss edge avg: {loss_avg:.4f}")
        rows.append(f"Signal: {'CORRECT' if win_avg>loss_avg else 'INVERTED'}")

    with open(EDGE_REPORT,"w") as f:

        for r in rows:
            f.write(r+"\n")

###############################################################
######################## SUMMARY ##############################
###############################################################

def summarize(df):

    wins=(df.bet_result=="Win").sum()
    losses=(df.bet_result=="Loss").sum()
    pushes=(df.bet_result=="Push").sum()

    total=wins+losses+pushes

    pct=wins/(wins+losses) if (wins+losses)>0 else 0

    return wins,losses,pushes,total,pct

###############################################################
######################## MARKET TALLY #########################
###############################################################

def build_market_tally(df,league):

    rows=[]

    for m in df.market_type.unique():

        sub=df[df.market_type==m]

        w,l,p,t,pct=summarize(sub)

        rows.append({

            "market":league,
            "market_type":m,
            "Win":w,
            "Loss":l,
            "Push":p,
            "Total":t,
            "Win_Pct":round(pct,4)

        })

    out=Path(f"docs/win/final_scores/results/market_tally_{league}.csv")

    pd.DataFrame(rows).to_csv(out,index=False)

###############################################################
######################## DEEP ANALYTICS #######################
###############################################################

def edge_bucket(val):

    if pd.isna(val):
        return ""

    if val<0.01: return "0-1%"
    if val<0.02: return "1-2%"
    if val<0.03: return "2-3%"
    if val<0.04: return "3-4%"
    if val<0.05: return "4-5%"

    return "5%+"

###############################################################
######################## DEEP SUMMARY #########################
###############################################################

def deep_summary(df,league):

    df["selected_edge"]=df.apply(extract_edge,axis=1)

    df["edge_bucket"]=df["selected_edge"].apply(edge_bucket)

    out=[]

    for bucket in sorted(df.edge_bucket.unique()):

        sub=df[df.edge_bucket==bucket]

        w,l,p,t,pct=summarize(sub)

        out.append({

            "market":league,
            "edge_bucket":bucket,
            "Win":w,
            "Loss":l,
            "Push":p,
            "Total":t,
            "Win_Pct":round(pct,4)

        })

    DEEP_SUMMARY_DIR.mkdir(parents=True,exist_ok=True)

    pd.DataFrame(out).to_csv(

        DEEP_SUMMARY_DIR / f"{league}_edge_bucket_summary.csv",
        index=False
    )

###############################################################
######################## MAIN #################################
###############################################################

def main():

    open(LOG_FILE,"w").close()

    for league in ["NBA","NCAAB"]:

        grade_league(league)

        build_master(league)

        path=NBA_OUTPUT/"NBA_final.csv" if league=="NBA" else NCAAB_OUTPUT/"NCAAB_final.csv"

        df=safe_read(path)

        if df.empty:
            continue

        build_market_tally(df,league)

        deep_summary(df,league)

    build_edge_report()

    print("Basketball results pipeline complete")


if __name__=="__main__":
    main()
