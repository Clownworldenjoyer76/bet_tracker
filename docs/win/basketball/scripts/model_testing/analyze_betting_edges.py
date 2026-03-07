#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/analyze_betting_edges.py

import pandas as pd
import numpy as np

FILE = "docs/win/basketball/model_testing/graded/NBA_final.csv"
FILE2 = "docs/win/basketball/model_testing/graded/NCAAB_final.csv"


def roi(df):
    if df.empty:
        return 0

    profit = 0

    for _, r in df.iterrows():
        odds = float(r["take_odds"])

        if r["bet_result"] == "Win":
            if odds > 0:
                profit += odds / 100
            else:
                profit += 100 / abs(odds)
        else:
            profit -= 1

    return profit / len(df)


def odds_band(x):

    bins = [-1000,-400,-300,-200,-150,-110,0,100,200,400,1000]

    for i in range(len(bins)-1):
        if bins[i] < x <= bins[i+1]:
            return f"{bins[i]} to {bins[i+1]}"

    return "other"


def analyze_moneyline(df,league):

    print(f"\n===== {league} MONEYLINE =====")

    ml = df[df.market_type=="moneyline"]

    ml["odds_band"] = ml["take_odds"].apply(odds_band)

    print("\nHOME vs AWAY")
    print(ml.groupby("bet_side")["bet_result"].value_counts())

    print("\nROI by side")
    for side in ["home","away"]:
        sub = ml[ml.bet_side==side]
        print(side,"sample:",len(sub),"ROI:",round(roi(sub),4))

    print("\nROI by odds band")

    bands = []

    for b,sub in ml.groupby("odds_band"):
        if len(sub) < 10:
            continue

        bands.append((b,len(sub),roi(sub)))

    bands = sorted(bands,key=lambda x:x[2],reverse=True)

    for b in bands[:10]:
        print(b)


def analyze_totals(df,league):

    print(f"\n===== {league} TOTAL EDGES =====")

    totals = df[df.market_type=="total"]

    bins = np.arange(0.02,0.30,0.01)

    best = []

    for b in bins:

        sub = totals[totals.candidate_edge >= b]

        if len(sub) < 20:
            continue

        best.append((b,len(sub),roi(sub)))

    best = sorted(best,key=lambda x:x[2],reverse=True)

    for r in best[:10]:
        print("edge >=",round(r[0],3),"sample",r[1],"roi",round(r[2],4))


def analyze_std(df,league):

    print(f"\n===== {league} STD TEST =====")

    results=[]

    for std in range(8,20):

        sub = df[df["config_total_std"]==std]

        if len(sub)<20:
            continue

        results.append((std,len(sub),roi(sub)))

    results=sorted(results,key=lambda x:x[2],reverse=True)

    print("\nBEST TOTAL STD")
    for r in results[:5]:
        print(r)

    results=[]

    for std in range(8,20):

        sub = df[df["config_spread_std"]==std]

        if len(sub)<20:
            continue

        results.append((std,len(sub),roi(sub)))

    results=sorted(results,key=lambda x:x[2],reverse=True)

    print("\nBEST SPREAD STD")
    for r in results[:5]:
        print(r)


def main():

    nba = pd.read_csv(FILE)
    ncaab = pd.read_csv(FILE2)

    analyze_moneyline(nba,"NBA")
    analyze_moneyline(ncaab,"NCAAB")

    analyze_totals(nba,"NBA")
    analyze_totals(ncaab,"NCAAB")

    analyze_std(nba,"NBA")
    analyze_std(ncaab,"NCAAB")


if __name__ == "__main__":
    main()
