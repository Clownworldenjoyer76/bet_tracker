#!/usr/bin/env python3

import itertools
import subprocess
import pandas as pd
import random
from pathlib import Path

# =========================================
# PARAMETER RANGES TO TEST
# =========================================

EDGE_MIN_VALUES = [0.08, 0.09, 0.10, 0.11]

SPREAD_MAX_VALUES = [12, 15, 18]

TOTAL_MIN_VALUES = [135, 140, 145]

ML_SKIP_RANGES = [
    (-180,-150),
    (-200,-140),
    (-160,-130)
]

MAX_RUNS = 20

# =========================================
# PIPELINE PATHS
# =========================================

PIPELINE = [

"docs/win/basketball/scripts/01_merge/build_juice_files.py",
"docs/win/basketball/scripts/02_apply_juice/apply_juice.py",
"docs/win/basketball/scripts/03_compute_edges/compute_edges.py",
"docs/win/basketball/scripts/04_select/select_bets.py",
"docs/win/final_scores/scripts/05_results/results.py"

]

OUTPUT = Path(
"docs/win/basketball/model_testing/rule_test_results.csv"
)

OUTPUT.parent.mkdir(parents=True,exist_ok=True)

# =========================================
# GENERATE RULE COMBINATIONS
# =========================================

grid = list(itertools.product(

EDGE_MIN_VALUES,
SPREAD_MAX_VALUES,
TOTAL_MIN_VALUES,
ML_SKIP_RANGES

))

if len(grid) > MAX_RUNS:

    grid = random.sample(grid,MAX_RUNS)

print("Running",len(grid),"rule tests")

results = []

# =========================================
# TEST LOOP
# =========================================

for EDGE_MIN,SPREAD_MAX,TOTAL_MIN,ML_RANGE in grid:

    print("Testing:",EDGE_MIN,SPREAD_MAX,TOTAL_MIN,ML_RANGE)

    config_file = Path(
    "docs/win/basketball/model_testing/rule_config.py"
    )

    with open(config_file,"w") as f:

        f.write(f"EDGE_MIN = {EDGE_MIN}\n")
        f.write(f"SPREAD_MAX = {SPREAD_MAX}\n")
        f.write(f"TOTAL_MIN = {TOTAL_MIN}\n")
        f.write(f"ML_LOW = {ML_RANGE[0]}\n")
        f.write(f"ML_HIGH = {ML_RANGE[1]}\n")

    # run pipeline

    for script in PIPELINE:

        subprocess.run(["python",script],check=True)

    # read results

    try:

        nba = pd.read_csv(
        "docs/win/final_scores/results/nba/market_tally.csv"
        )

        ncaab = pd.read_csv(
        "docs/win/final_scores/results/ncaab/market_tally.csv"
        )

        nba_spread = nba.loc[
        nba.market_type=="spread","Win_Pct"].values[0]

        ncaab_spread = ncaab.loc[
        ncaab.market_type=="spread","Win_Pct"].values[0]

    except:

        nba_spread = None
        ncaab_spread = None

    results.append({

        "EDGE_MIN":EDGE_MIN,
        "SPREAD_MAX":SPREAD_MAX,
        "TOTAL_MIN":TOTAL_MIN,
        "ML_RANGE":ML_RANGE,

        "NBA_SPREAD_WIN_PCT":nba_spread,
        "NCAAB_SPREAD_WIN_PCT":ncaab_spread

    })

df = pd.DataFrame(results)

df = df.sort_values(
"NBA_SPREAD_WIN_PCT",
ascending=False
)

df.to_csv(OUTPUT,index=False)

print("Rule optimization complete")
print("Results saved:",OUTPUT)
