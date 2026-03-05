#!/usr/bin/env python3

import itertools
import subprocess
import pandas as pd
import random
from pathlib import Path

# =========================================
# RUN DATE (merge_intake.py requires this)
# =========================================

RUN_DATE = "2026_02_24"

# =========================================
# PARAMETER RANGES TO TEST
# =========================================

EDGE_MIN_VALUES = [0.08, 0.09, 0.10, 0.11]
SPREAD_MAX_VALUES = [12, 15, 18]
TOTAL_MIN_VALUES = [135, 140, 145]

ML_SKIP_RANGES = [
    (-180, -150),
    (-200, -140),
    (-160, -130),
]

MAX_RUNS = 20

# =========================================
# PIPELINES
# =========================================

# run once (expensive)
BASE_PIPELINE = [
    "docs/win/basketball/scripts/01_merge/merge_intake.py",
    "docs/win/basketball/scripts/01_merge/build_juice_files.py",
    "docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py",
    "docs/win/basketball/scripts/02_juice/apply_spread_juice.py",
    "docs/win/basketball/scripts/02_juice/apply_total_juice.py",
    "docs/win/basketball/scripts/03_edges/compute_edges.py",
]

# run every rule set (fast)
RULE_PIPELINE = [
    "docs/win/basketball/scripts/04_select/select_bets.py",
    "docs/win/basketball/scripts/04_select/combine_trim_basketball.py",
    "docs/win/final_scores/scripts/05_results/results.py",
]

OUTPUT = Path("docs/win/basketball/model_testing/rule_test_results.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# =========================================
# GENERATE RULE COMBINATIONS
# =========================================

grid = list(
    itertools.product(
        EDGE_MIN_VALUES,
        SPREAD_MAX_VALUES,
        TOTAL_MIN_VALUES,
        ML_SKIP_RANGES,
    )
)

if len(grid) > MAX_RUNS:
    grid = random.sample(grid, MAX_RUNS)

print("Running", len(grid), "rule tests")

# =========================================
# RUN BASE PIPELINE ONCE
# =========================================

print("Running base pipeline for date:", RUN_DATE)

for script in BASE_PIPELINE:
    print("Running:", script)

    # merge_intake.py requires YYYY_MM_DD
    if script.endswith("merge_intake.py"):
        subprocess.run(["python", script, RUN_DATE], check=True)
    else:
        subprocess.run(["python", script], check=True)

print("Base pipeline complete")

# =========================================
# TEST LOOP
# =========================================

results = []
config_file = Path("docs/win/basketball/model_testing/rule_config.py")

for EDGE_MIN, SPREAD_MAX, TOTAL_MIN, ML_RANGE in grid:
    print("Testing:", EDGE_MIN, SPREAD_MAX, TOTAL_MIN, ML_RANGE)

    with open(config_file, "w", encoding="utf-8") as f:
        f.write(f"EDGE_MIN = {EDGE_MIN}\n")
        f.write(f"SPREAD_MAX = {SPREAD_MAX}\n")
        f.write(f"TOTAL_MIN = {TOTAL_MIN}\n")
        f.write(f"ML_LOW = {ML_RANGE[0]}\n")
        f.write(f"ML_HIGH = {ML_RANGE[1]}\n")

    # run rule pipeline
    for script in RULE_PIPELINE:
        subprocess.run(["python", script], check=True)

    # read results
    nba_spread = None
    ncaab_spread = None

    try:
        nba = pd.read_csv("docs/win/final_scores/results/nba/market_tally.csv")
        ncaab = pd.read_csv("docs/win/final_scores/results/ncaab/market_tally.csv")

        nba_vals = nba.loc[nba.market_type == "spread", "Win_Pct"].values
        ncaab_vals = ncaab.loc[ncaab.market_type == "spread", "Win_Pct"].values

        nba_spread = float(nba_vals[0]) if len(nba_vals) else None
        ncaab_spread = float(ncaab_vals[0]) if len(ncaab_vals) else None
    except Exception:
        nba_spread = None
        ncaab_spread = None

    results.append(
        {
            "RUN_DATE": RUN_DATE,
            "EDGE_MIN": EDGE_MIN,
            "SPREAD_MAX": SPREAD_MAX,
            "TOTAL_MIN": TOTAL_MIN,
            "ML_LOW": ML_RANGE[0],
            "ML_HIGH": ML_RANGE[1],
            "NBA_SPREAD_WIN_PCT": nba_spread,
            "NCAAB_SPREAD_WIN_PCT": ncaab_spread,
        }
    )

# =========================================
# OUTPUT RESULTS
# =========================================

df = pd.DataFrame(results)

# Sort safely even if some rows are None
df["NBA_SPREAD_WIN_PCT_SORT"] = pd.to_numeric(df["NBA_SPREAD_WIN_PCT"], errors="coerce")
df = df.sort_values("NBA_SPREAD_WIN_PCT_SORT", ascending=False).drop(columns=["NBA_SPREAD_WIN_PCT_SORT"])

df.to_csv(OUTPUT, index=False)

print("Rule optimization complete")
print("Results saved:", OUTPUT)
