#!/usr/bin/env python3

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

EDGE_MIN_VALUES = [0.00, 0.20]
SPREAD_MAX_VALUES = [2, 20]
TOTAL_MIN_VALUES = [120, 160]

ML_SKIP_RANGES = [
    (-400, -300),
    (-250, -200),
    (-160, -140),
    (-120, -110),
    (-105, 200),
]

MAX_RUNS = 4

# =========================================
# PIPELINES
# =========================================

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
    "docs/win/final_scores/scripts/05_results/results.py",
]

OUTPUT = Path("docs/win/basketball/model_testing/rule_test_results.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = Path("docs/win/basketball/model_testing/rule_config.py")

# =========================================
# GENERATE PARAMETER GRID
# =========================================

grid = list(itertools.product(
    EDGE_MIN_VALUES,
    SPREAD_MAX_VALUES,
    TOTAL_MIN_VALUES,
    ML_SKIP_RANGES
))

if len(grid) > MAX_RUNS:
    grid = random.sample(grid, MAX_RUNS)

print("Running", len(grid), "rule tests")

results = []

# =========================================
# DATE LOOP
# =========================================

for RUN_DATE in RUN_DATES:

    print("\nRunning base pipeline for:", RUN_DATE)

    for script in BASE_PIPELINE:
        subprocess.run(["python", script], check=True)

    print("Base pipeline complete for", RUN_DATE)

    # =========================================
    # RULE LOOP
    # =========================================

    for EDGE_MIN, SPREAD_MAX, TOTAL_MIN, ML_RANGE in grid:

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"EDGE_MIN = {EDGE_MIN}\n")
            f.write(f"SPREAD_MAX = {SPREAD_MAX}\n")
            f.write(f"TOTAL_MIN = {TOTAL_MIN}\n")
            f.write(f"ML_LOW = {ML_RANGE[0]}\n")
            f.write(f"ML_HIGH = {ML_RANGE[1]}\n")

        for script in RULE_PIPELINE:
            subprocess.run(["python", script], check=True)

        try:

            nba = pd.read_csv(
                "docs/win/final_scores/results/nba/market_tally.csv"
            )
            ncaab = pd.read_csv(
                "docs/win/final_scores/results/ncaab/market_tally.csv"
            )

            nba_vals = nba.loc[nba.market_type == "spread", "Win_Pct"].values
            ncaab_vals = ncaab.loc[ncaab.market_type == "spread", "Win_Pct"].values

            nba_spread = float(nba_vals[0]) if len(nba_vals) else None
            ncaab_spread = float(ncaab_vals[0]) if len(ncaab_vals) else None

        except Exception:
            nba_spread = None
            ncaab_spread = None

        results.append({
            "RUN_DATE": RUN_DATE,
            "EDGE_MIN": EDGE_MIN,
            "SPREAD_MAX": SPREAD_MAX,
            "TOTAL_MIN": TOTAL_MIN,
            "ML_LOW": ML_RANGE[0],
            "ML_HIGH": ML_RANGE[1],
            "NBA_SPREAD_WIN_PCT": nba_spread,
            "NCAAB_SPREAD_WIN_PCT": ncaab_spread
        })

# =========================================
# SAVE RESULTS
# =========================================

df = pd.DataFrame(results)

df["NBA_SORT"] = pd.to_numeric(df["NBA_SPREAD_WIN_PCT"], errors="coerce")

df = df.sort_values("NBA_SORT", ascending=False).drop(columns=["NBA_SORT"])

df.to_csv(OUTPUT, index=False)

print("\nRule optimization complete")
print("Results saved:", OUTPUT)
