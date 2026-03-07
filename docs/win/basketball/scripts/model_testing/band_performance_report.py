#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/band_performance_report.py

import pandas as pd
from pathlib import Path

NBA_FILE = Path("docs/win/basketball/model_testing/graded/nba/NBA_final.csv")
NCAAB_FILE = Path("docs/win/basketball/model_testing/graded/ncaab/NCAAB_final.csv")

OUTPUT = Path("docs/win/basketball/model_testing/band_performance_report.csv")


ML_BINS = [-1000,-400,-300,-200,-150,-110,0,100,200,400,1000]
SPREAD_BINS = [-30,-15,-10,-7,-5,-3,-1,0,1,3,5,7,10,15,30]
TOTAL_BINS = [120,130,135,140,145,150,155,160,165,170,200]


def bucket(series, bins):
    return pd.cut(series, bins=bins, include_lowest=True)


def build_table(df, league):

    rows = []

    # MONEYLINE
    ml = df[df.market_type == "moneyline"]

    for side in ["home","away"]:
        sub = ml[ml.bet_side == side].copy()
        if sub.empty:
            continue

        sub["band"] = bucket(sub["line"], ML_BINS)

        g = sub.groupby("band")

        for band,grp in g:
            bets=len(grp)
            wins=(grp.bet_result=="Win").sum()

            rows.append({
                "league":league,
                "market_type":"moneyline",
                "side":side,
                "band":str(band),
                "bets":bets,
                "wins":wins,
                "win_pct":wins/bets if bets else 0
            })

    # SPREAD
    sp = df[df.market_type=="spread"].copy()

    for side in ["home","away"]:
        sub = sp[sp.bet_side==side].copy()
        if sub.empty:
            continue

        sub["band"]=bucket(sub["line"],SPREAD_BINS)

        g=sub.groupby("band")

        for band,grp in g:

            bets=len(grp)
            wins=(grp.bet_result=="Win").sum()

            rows.append({
                "league":league,
                "market_type":"spread",
                "side":side,
                "band":str(band),
                "bets":bets,
                "wins":wins,
                "win_pct":wins/bets if bets else 0
            })

    # TOTALS
    tot=df[df.market_type=="total"].copy()

    for side in ["over","under"]:
        sub=tot[tot.bet_side==side].copy()
        if sub.empty:
            continue

        sub["band"]=bucket(sub["line"],TOTAL_BINS)

        g=sub.groupby("band")

        for band,grp in g:

            bets=len(grp)
            wins=(grp.bet_result=="Win").sum()

            rows.append({
                "league":league,
                "market_type":"total",
                "side":side,
                "band":str(band),
                "bets":bets,
                "wins":wins,
                "win_pct":wins/bets if bets else 0
            })

    return rows


def main():

    rows=[]

    if NBA_FILE.exists():
        nba=pd.read_csv(NBA_FILE)
        rows+=build_table(nba,"NBA")

    if NCAAB_FILE.exists():
        ncaa=pd.read_csv(NCAAB_FILE)
        rows+=build_table(ncaa,"NCAAB")

    df=pd.DataFrame(rows)

    if not df.empty:
        df=df.sort_values(["league","market_type","side","band"])

    df.to_csv(OUTPUT,index=False)


if __name__=="__main__":
    main()
