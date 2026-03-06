#!/usr/bin/env python3
# docs/win/hockey/scripts/model_testing/run_parameter_tests.py

import itertools
import subprocess
import pandas as pd
import random
from pathlib import Path

# =========================================
# RUN DATES
# =========================================

RUN_DATES = [
    "2026_02_24",
    "2026_02_26",
    "2026_02_27",
    "2026_03_01",
    "2026_03_02",
    "2026_03_03",
    "2026_03_04",
]

# =========================================
# PARAMETER RANGES
# =========================================

TOTAL_MIN_EDGE_PCT_VALUES = [0.03,0.04,0.05,0.06,0.07]
TOTAL_MIN_PROB_VALUES = [0.50,0.52,0.54,0.56]

PL_DOG_WIN_PROB_REQ_VALUES = [0.42,0.45,0.48,0.50]
PL_HUGE_FAV_EDGE_VALUES = [0.12,0.15,0.18,0.20,0.22]
PL_MAX_FAV_ODDS_VALUES = [-140,-130,-120,-110]

ML_MIN_EDGE_VALUES = [0.02,0.03,0.04,0.05]
ML_MIN_PROB_VALUES = [0.42,0.45,0.48,0.50]

MAX_RUNS = 300

# =========================================
# PIPELINES
# =========================================

BASE_PIPELINE = [
    "docs/win/hockey/scripts/01_merge/build_juice_files.py",
    "docs/win/hockey/scripts/02_juice/apply_moneyline_juice.py",
    "docs/win/hockey/scripts/02_juice/apply_puck_line_juice.py",
    "docs/win/hockey/scripts/02_juice/apply_total_juice.py",
    "docs/win/hockey/scripts/03_edges/compute_edges.py",
]

RULE_PIPELINE = [
    "docs/win/hockey/scripts/04_select/select_bets.py",
    "docs/win/final_scores/scripts/05_results/results.py",
]

OUTPUT = Path("docs/win/hockey/model_testing/rule_test_results.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = Path("docs/win/hockey/model_testing/rule_config.py")

# =========================================
# GENERATE GRID
# =========================================

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

print("Running", len(grid), "rule combinations")

results = []

# =========================================
# DATE LOOP
# =========================================

for RUN_DATE in RUN_DATES:

    print("\n==============================")
    print("Processing date:", RUN_DATE)
    print("==============================")

    # run expensive pipeline once per date
    for script in BASE_PIPELINE:
        print("Running:", script)
        subprocess.run(["python", script], check=True)

    print("Base pipeline complete")

    # =====================================
    # RULE LOOP
    # =====================================

    for (
        TOTAL_MIN_EDGE_PCT,
        TOTAL_MIN_PROB,
        PL_DOG_WIN_PROB_REQ,
        PL_HUGE_FAV_EDGE,
        PL_MAX_FAV_ODDS,
        ML_MIN_EDGE,
        ML_MIN_PROB
    ) in grid:

        with open(CONFIG_FILE,"w",encoding="utf-8") as f:

            f.write(f"TOTAL_MIN_EDGE_PCT = {TOTAL_MIN_EDGE_PCT}\n")
            f.write(f"TOTAL_MIN_PROB = {TOTAL_MIN_PROB}\n")
            f.write(f"PL_DOG_WIN_PROB_REQ = {PL_DOG_WIN_PROB_REQ}\n")
            f.write(f"PL_HUGE_FAV_EDGE = {PL_HUGE_FAV_EDGE}\n")
            f.write(f"PL_MAX_FAV_ODDS = {PL_MAX_FAV_ODDS}\n")
            f.write(f"ML_MIN_EDGE = {ML_MIN_EDGE}\n")
            f.write(f"ML_MIN_PROB = {ML_MIN_PROB}\n")

        # run rule pipeline
        for script in RULE_PIPELINE:
            subprocess.run(["python", script], check=True)

        # =====================================
        # READ RESULTS
        # =====================================

        try:

            nhl = pd.read_csv(
                "docs/win/final_scores/results/nhl/market_tally.csv"
            )

            moneyline_vals = nhl.loc[
                nhl.market_type=="moneyline","Win_Pct"
            ].values

            puck_line_vals = nhl.loc[
                nhl.market_type=="puck_line","Win_Pct"
            ].values

            total_vals = nhl.loc[
                nhl.market_type=="total","Win_Pct"
            ].values

            moneyline_win_pct = float(moneyline_vals[0]) if len(moneyline_vals) else None
            puck_line_win_pct = float(puck_line_vals[0]) if len(puck_line_vals) else None
            total_win_pct = float(total_vals[0]) if len(total_vals) else None

        except Exception:

            moneyline_win_pct = None
            puck_line_win_pct = None
            total_win_pct = None

        results.append({

            "RUN_DATE": RUN_DATE,

            "TOTAL_MIN_EDGE_PCT": TOTAL_MIN_EDGE_PCT,
            "TOTAL_MIN_PROB": TOTAL_MIN_PROB,

            "PL_DOG_WIN_PROB_REQ": PL_DOG_WIN_PROB_REQ,
            "PL_HUGE_FAV_EDGE": PL_HUGE_FAV_EDGE,
            "PL_MAX_FAV_ODDS": PL_MAX_FAV_ODDS,

            "ML_MIN_EDGE": ML_MIN_EDGE,
            "ML_MIN_PROB": ML_MIN_PROB,

            "NHL_MONEYLINE_WIN_PCT": moneyline_win_pct,
            "NHL_PUCK_LINE_WIN_PCT": puck_line_win_pct,
            "NHL_TOTAL_WIN_PCT": total_win_pct

        })

        # write incremental results
        pd.DataFrame(results).to_csv(OUTPUT,index=False)

# =========================================
# FINAL SORT
# =========================================

df = pd.DataFrame(results)

df["NHL_PUCK_LINE_WIN_PCT_SORT"] = pd.to_numeric(
    df["NHL_PUCK_LINE_WIN_PCT"],
    errors="coerce"
)

df["NHL_TOTAL_WIN_PCT_SORT"] = pd.to_numeric(
    df["NHL_TOTAL_WIN_PCT"],
    errors="coerce"
)

df = df.sort_values(
    ["NHL_PUCK_LINE_WIN_PCT_SORT","NHL_TOTAL_WIN_PCT_SORT"],
    ascending=[False,False]
).drop(columns=[
    "NHL_PUCK_LINE_WIN_PCT_SORT",
    "NHL_TOTAL_WIN_PCT_SORT"
])

df.to_csv(OUTPUT,index=False)

print("Optimization complete")
print("Results saved:",OUTPUT)
