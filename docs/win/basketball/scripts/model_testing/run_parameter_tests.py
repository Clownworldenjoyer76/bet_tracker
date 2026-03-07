#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/run_parameter_tests.py

import itertools
import subprocess
import pandas as pd
import random
import shutil
from pathlib import Path

RUN_DATES = [
    "2026_02_24",
    "2026_02_26",
    "2026_02_27",
    "2026_03_01",
    "2026_03_02",
    "2026_03_03",
    "2026_03_04",
]

NBA_TOTAL_STD_VALUES = [12,14,16]
NBA_SPREAD_STD_VALUES = [13,15,17]

NCAAB_TOTAL_STD_VALUES = [10,12,14]
NCAAB_SPREAD_STD_VALUES = [13,15,17]

MAX_RUNS = 5

BASE_PIPELINE = [
    "docs/win/basketball/scripts/model_testing/build_juice_files.py",
    "docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py",
    "docs/win/basketball/scripts/02_juice/apply_spread_juice.py",
    "docs/win/basketball/scripts/02_juice/apply_total_juice.py",
    "docs/win/basketball/scripts/model_testing/compute_edges.py",
]

RULE_PIPELINE = [
    "docs/win/basketball/scripts/model_testing/select_bets_optimizer.py",
    "docs/win/basketball/scripts/model_testing/combine_trim_basketball.py",
    "docs/win/basketball/scripts/model_testing/basketball_results.py",
    "docs/win/basketball/scripts/model_testing/band_performance_report.py",
]

CONFIG_FILE = Path("docs/win/basketball/model_testing/rule_config.py")

OUTPUT = Path("docs/win/basketball/model_testing/rule_test_results.csv")

NBA_FINAL = Path("docs/win/basketball/model_testing/graded/nba/NBA_final.csv")
NCAAB_FINAL = Path("docs/win/basketball/model_testing/graded/ncaab/NCAAB_final.csv")

grid = list(itertools.product(
    NBA_TOTAL_STD_VALUES,
    NBA_SPREAD_STD_VALUES,
    NCAAB_TOTAL_STD_VALUES,
    NCAAB_SPREAD_STD_VALUES
))

if len(grid) > MAX_RUNS:
    grid = random.sample(grid, MAX_RUNS)

results=[]

def win_pct(df):
    if df.empty:
        return 0
    return (df.bet_result=="Win").mean()

for RUN_DATE in RUN_DATES:

    for params in grid:

        NBA_TOTAL_STD,NBA_SPREAD_STD,NCAAB_TOTAL_STD,NCAAB_SPREAD_STD=params

        with open(CONFIG_FILE,"w") as f:

            f.write(f'RUN_DATE="{RUN_DATE}"\n')
            f.write(f"NBA_TOTAL_STD={NBA_TOTAL_STD}\n")
            f.write(f"NBA_SPREAD_STD={NBA_SPREAD_STD}\n")
            f.write(f"NCAAB_TOTAL_STD={NCAAB_TOTAL_STD}\n")
            f.write(f"NCAAB_SPREAD_STD={NCAAB_SPREAD_STD}\n")

        shutil.rmtree("docs/win/basketball/model_testing/graded",ignore_errors=True)

        for script in BASE_PIPELINE:
            subprocess.run(["python",script],check=True)

        for script in RULE_PIPELINE:
            subprocess.run(["python",script],check=True)

        row={
            "RUN_DATE":RUN_DATE,
            "NBA_TOTAL_STD":NBA_TOTAL_STD,
            "NBA_SPREAD_STD":NBA_SPREAD_STD,
            "NCAAB_TOTAL_STD":NCAAB_TOTAL_STD,
            "NCAAB_SPREAD_STD":NCAAB_SPREAD_STD
        }

        if NBA_FINAL.exists():

            nba=pd.read_csv(NBA_FINAL)

            row["NBA_ML_HOME_WIN_PCT"]=win_pct(nba[(nba.market_type=="moneyline")&(nba.bet_side=="home")])
            row["NBA_ML_AWAY_WIN_PCT"]=win_pct(nba[(nba.market_type=="moneyline")&(nba.bet_side=="away")])

            row["NBA_TOTAL_WIN_PCT"]=win_pct(nba[nba.market_type=="total"])
            row["NBA_SPREAD_WIN_PCT"]=win_pct(nba[nba.market_type=="spread"])

        if NCAAB_FINAL.exists():

            ncaa=pd.read_csv(NCAAB_FINAL)

            row["NCAAB_ML_HOME_WIN_PCT"]=win_pct(ncaa[(ncaa.market_type=="moneyline")&(ncaa.bet_side=="home")])
            row["NCAAB_ML_AWAY_WIN_PCT"]=win_pct(ncaa[(ncaa.market_type=="moneyline")&(ncaa.bet_side=="away")])

            row["NCAAB_TOTAL_WIN_PCT"]=win_pct(ncaa[ncaa.market_type=="total"])
            row["NCAAB_SPREAD_WIN_PCT"]=win_pct(ncaa[ncaa.market_type=="spread"])

        results.append(row)

df=pd.DataFrame(results)

df.to_csv(OUTPUT,index=False)

print("Parameter tests complete")
