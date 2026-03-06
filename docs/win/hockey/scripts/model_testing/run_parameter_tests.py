#!/usr/bin/env python3
# docs/win/hockey/scripts/model_testing/run_parameter_tests.py

import itertools
import subprocess
import pandas as pd
import random
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

TOTAL_MIN_EDGE_PCT_VALUES = [0.03,0.04,0.05,0.06,0.07]
TOTAL_MIN_PROB_VALUES = [0.50,0.52,0.54,0.56]

PL_DOG_WIN_PROB_REQ_VALUES = [0.42,0.45,0.48,0.50]
PL_HUGE_FAV_EDGE_VALUES = [0.12,0.15,0.18,0.20,0.22]
PL_MAX_FAV_ODDS_VALUES = [-140,-130,-120,-110]

ML_MIN_EDGE_VALUES = [0.02,0.03,0.04,0.05]
ML_MIN_PROB_VALUES = [0.42,0.45,0.48,0.50]

MAX_RUNS = 5

BASE_PIPELINE = [
    "docs/win/hockey/scripts/model_testing/build_juice_files.py",
    "docs/win/hockey/scripts/02_juice/apply_moneyline_juice.py",
    "docs/win/hockey/scripts/02_juice/apply_puck_line_juice.py",
    "docs/win/hockey/scripts/02_juice/apply_total_juice.py",
    "docs/win/hockey/scripts/model_testing/compute_edges.py",
]

RULE_PIPELINE = [
    "docs/win/hockey/scripts/model_testing/select_bets.py",
    "docs/win/final_scores/scripts/05_results/results.py",
]

OUTPUT = Path("docs/win/hockey/model_testing/rule_test_results.csv")
CONFIG_FILE = Path("docs/win/hockey/model_testing/rule_config.py")

grid = list(itertools.product(
    TOTAL_MIN_EDGE_PCT_VALUES,
    TOTAL_MIN_PROB_VALUES,
    PL_DOG_WIN_PROB_REQ_VALUES,
    PL_HUGE_FAV_EDGE_VALUES,
    PL_MAX_FAV_ODDS_VALUES,
    ML_MIN_EDGE_VALUES,
    ML_MIN_PROB_VALUES
))

if len(grid) > MAX_RUNS:
    grid = random.sample(grid, MAX_RUNS)

results = []

for RUN_DATE in RUN_DATES:

    for script in BASE_PIPELINE:
        subprocess.run(["python", script], check=True)

    for params in grid:

        (
            TOTAL_MIN_EDGE_PCT,
            TOTAL_MIN_PROB,
            PL_DOG_WIN_PROB_REQ,
            PL_HUGE_FAV_EDGE,
            PL_MAX_FAV_ODDS,
            ML_MIN_EDGE,
            ML_MIN_PROB
        ) = params

        with open(CONFIG_FILE,"w") as f:
            f.write(f"TOTAL_MIN_EDGE_PCT = {TOTAL_MIN_EDGE_PCT}\n")
            f.write(f"TOTAL_MIN_PROB = {TOTAL_MIN_PROB}\n")
            f.write(f"PL_DOG_WIN_PROB_REQ = {PL_DOG_WIN_PROB_REQ}\n")
            f.write(f"PL_HUGE_FAV_EDGE = {PL_HUGE_FAV_EDGE}\n")
            f.write(f"PL_MAX_FAV_ODDS = {PL_MAX_FAV_ODDS}\n")
            f.write(f"ML_MIN_EDGE = {ML_MIN_EDGE}\n")
            f.write(f"ML_MIN_PROB = {ML_MIN_PROB}\n")

        for script in RULE_PIPELINE:
            subprocess.run(["python", script], check=True)

        try:
            nhl = pd.read_csv("docs/win/final_scores/results/nhl/market_tally.csv")

            moneyline = nhl.loc[nhl.market_type=="moneyline","Win_Pct"].values
            puckline = nhl.loc[nhl.market_type=="puck_line","Win_Pct"].values
            total = nhl.loc[nhl.market_type=="total","Win_Pct"].values

            moneyline = float(moneyline[0]) if len(moneyline) else None
            puckline = float(puckline[0]) if len(puckline) else None
            total = float(total[0]) if len(total) else None

        except:
            moneyline = None
            puckline = None
            total = None

        results.append({
            "RUN_DATE": RUN_DATE,
            "TOTAL_MIN_EDGE_PCT": TOTAL_MIN_EDGE_PCT,
            "TOTAL_MIN_PROB": TOTAL_MIN_PROB,
            "PL_DOG_WIN_PROB_REQ": PL_DOG_WIN_PROB_REQ,
            "PL_HUGE_FAV_EDGE": PL_HUGE_FAV_EDGE,
            "PL_MAX_FAV_ODDS": PL_MAX_FAV_ODDS,
            "ML_MIN_EDGE": ML_MIN_EDGE,
            "ML_MIN_PROB": ML_MIN_PROB,
            "NHL_MONEYLINE_WIN_PCT": moneyline,
            "NHL_PUCK_LINE_WIN_PCT": puckline,
            "NHL_TOTAL_WIN_PCT": total
        })

        pd.DataFrame(results).to_csv(OUTPUT,index=False)

print("Optimization complete")
