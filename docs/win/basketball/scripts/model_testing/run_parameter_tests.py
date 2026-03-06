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

EDGE_MAX_VALUES = [0.30]
SPREAD_MAX_VALUES = [2, 20]
TOTAL_MIN_VALUES = [120, 160]

NBA_TOTAL_STD_VALUES = [14]
NBA_SPREAD_STD_VALUES = [15]
NCAAB_TOTAL_STD_VALUES = [12]
NCAAB_SPREAD_STD_VALUES = [15]

NBA_TOTAL_EDGE_VALUES = [0.05]
NBA_SPREAD_EDGE_VALUES = [0.05]
NBA_ML_HOME_EDGE_VALUES = [0.05]
NBA_ML_AWAY_EDGE_VALUES = [0.05]

NCAAB_TOTAL_EDGE_VALUES = [0.05]
NCAAB_SPREAD_EDGE_VALUES = [0.05]
NCAAB_ML_HOME_EDGE_VALUES = [0.05]
NCAAB_ML_AWAY_EDGE_VALUES = [0.05]

NBA_TOTAL_EDGE_MIN_VALUES = [0.00]
NCAAB_TOTAL_EDGE_MIN_VALUES = [0.00]
NBA_SPREAD_EDGE_MIN_VALUES = [0.00]
NCAAB_SPREAD_EDGE_MIN_VALUES = [0.00]

NBA_ML_HOME_EDGE_MIN_VALUES = [0.00]
NBA_ML_AWAY_EDGE_MIN_VALUES = [0.00]
NCAAB_ML_HOME_EDGE_MIN_VALUES = [0.00]
NCAAB_ML_AWAY_EDGE_MIN_VALUES = [0.00]

NBA_ML_HOME_ODDS_RANGES = [(-10000, 10000)]
NBA_ML_AWAY_ODDS_RANGES = [(-10000, 10000)]
NCAAB_ML_HOME_ODDS_RANGES = [(-400, -300), (-105, 200)]
NCAAB_ML_AWAY_ODDS_RANGES = [(-10000, 10000)]

MAX_RUNS = 2

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
]

OUTPUT = Path("docs/win/basketball/model_testing/rule_test_results.csv")
CONFIG_FILE = Path("docs/win/basketball/model_testing/rule_config.py")
OPTIMIZER_STATS = Path("docs/win/basketball/model_testing/optimizer_stats.csv")
NBA_STATS = Path("docs/win/basketball/model_testing/graded/nba/NBA_stats.csv")
NCAAB_STATS = Path("docs/win/basketball/model_testing/graded/ncaab/NCAAB_stats.csv")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

grid = list(itertools.product(
    EDGE_MAX_VALUES,
    SPREAD_MAX_VALUES,
    TOTAL_MIN_VALUES,
    NBA_TOTAL_STD_VALUES,
    NBA_SPREAD_STD_VALUES,
    NCAAB_TOTAL_STD_VALUES,
    NCAAB_SPREAD_STD_VALUES,
    NBA_TOTAL_EDGE_VALUES,
    NBA_SPREAD_EDGE_VALUES,
    NBA_ML_HOME_EDGE_VALUES,
    NBA_ML_AWAY_EDGE_VALUES,
    NCAAB_TOTAL_EDGE_VALUES,
    NCAAB_SPREAD_EDGE_VALUES,
    NCAAB_ML_HOME_EDGE_VALUES,
    NCAAB_ML_AWAY_EDGE_VALUES,
    NBA_TOTAL_EDGE_MIN_VALUES,
    NCAAB_TOTAL_EDGE_MIN_VALUES,
    NBA_SPREAD_EDGE_MIN_VALUES,
    NCAAB_SPREAD_EDGE_MIN_VALUES,
    NBA_ML_HOME_EDGE_MIN_VALUES,
    NBA_ML_AWAY_EDGE_MIN_VALUES,
    NCAAB_ML_HOME_EDGE_MIN_VALUES,
    NCAAB_ML_AWAY_EDGE_MIN_VALUES,
    NBA_ML_HOME_ODDS_RANGES,
    NBA_ML_AWAY_ODDS_RANGES,
    NCAAB_ML_HOME_ODDS_RANGES,
    NCAAB_ML_AWAY_ODDS_RANGES,
))

if len(grid) > MAX_RUNS:
    grid = random.sample(grid, MAX_RUNS)

print("Running", len(grid), "rule tests")

results = []

for RUN_DATE in RUN_DATES:

    print("\nRunning base pipeline for:", RUN_DATE)

    for params in grid:

        (
            EDGE_MAX,
            SPREAD_MAX,
            TOTAL_MIN,
            NBA_TOTAL_STD,
            NBA_SPREAD_STD,
            NCAAB_TOTAL_STD,
            NCAAB_SPREAD_STD,
            NBA_TOTAL_EDGE,
            NBA_SPREAD_EDGE,
            NBA_ML_HOME_EDGE,
            NBA_ML_AWAY_EDGE,
            NCAAB_TOTAL_EDGE,
            NCAAB_SPREAD_EDGE,
            NCAAB_ML_HOME_EDGE,
            NCAAB_ML_AWAY_EDGE,
            NBA_TOTAL_EDGE_MIN,
            NCAAB_TOTAL_EDGE_MIN,
            NBA_SPREAD_EDGE_MIN,
            NCAAB_SPREAD_EDGE_MIN,
            NBA_ML_HOME_EDGE_MIN,
            NBA_ML_AWAY_EDGE_MIN,
            NCAAB_ML_HOME_EDGE_MIN,
            NCAAB_ML_AWAY_EDGE_MIN,
            NBA_ML_HOME_ODDS_RANGE,
            NBA_ML_AWAY_ODDS_RANGE,
            NCAAB_ML_HOME_ODDS_RANGE,
            NCAAB_ML_AWAY_ODDS_RANGE,
        ) = params

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f'RUN_DATE = "{RUN_DATE}"\n')
            f.write(f"EDGE_MAX = {EDGE_MAX}\n")
            f.write(f"SPREAD_MAX = {SPREAD_MAX}\n")
            f.write(f"TOTAL_MIN = {TOTAL_MIN}\n")

            f.write(f"NBA_TOTAL_STD = {NBA_TOTAL_STD}\n")
            f.write(f"NBA_SPREAD_STD = {NBA_SPREAD_STD}\n")
            f.write(f"NCAAB_TOTAL_STD = {NCAAB_TOTAL_STD}\n")
            f.write(f"NCAAB_SPREAD_STD = {NCAAB_SPREAD_STD}\n")

            f.write(f"NBA_TOTAL_EDGE = {NBA_TOTAL_EDGE}\n")
            f.write(f"NBA_SPREAD_EDGE = {NBA_SPREAD_EDGE}\n")
            f.write(f"NBA_ML_HOME_EDGE = {NBA_ML_HOME_EDGE}\n")
            f.write(f"NBA_ML_AWAY_EDGE = {NBA_ML_AWAY_EDGE}\n")

            f.write(f"NCAAB_TOTAL_EDGE = {NCAAB_TOTAL_EDGE}\n")
            f.write(f"NCAAB_SPREAD_EDGE = {NCAAB_SPREAD_EDGE}\n")
            f.write(f"NCAAB_ML_HOME_EDGE = {NCAAB_ML_HOME_EDGE}\n")
            f.write(f"NCAAB_ML_AWAY_EDGE = {NCAAB_ML_AWAY_EDGE}\n")

            f.write(f"NBA_TOTAL_EDGE_MIN = {NBA_TOTAL_EDGE_MIN}\n")
            f.write(f"NCAAB_TOTAL_EDGE_MIN = {NCAAB_TOTAL_EDGE_MIN}\n")
            f.write(f"NBA_SPREAD_EDGE_MIN = {NBA_SPREAD_EDGE_MIN}\n")
            f.write(f"NCAAB_SPREAD_EDGE_MIN = {NCAAB_SPREAD_EDGE_MIN}\n")

            f.write(f"NBA_ML_HOME_EDGE_MIN = {NBA_ML_HOME_EDGE_MIN}\n")
            f.write(f"NBA_ML_AWAY_EDGE_MIN = {NBA_ML_AWAY_EDGE_MIN}\n")
            f.write(f"NCAAB_ML_HOME_EDGE_MIN = {NCAAB_ML_HOME_EDGE_MIN}\n")
            f.write(f"NCAAB_ML_AWAY_EDGE_MIN = {NCAAB_ML_AWAY_EDGE_MIN}\n")

            f.write(f"NBA_ML_HOME_ODDS_MIN = {NBA_ML_HOME_ODDS_RANGE[0]}\n")
            f.write(f"NBA_ML_HOME_ODDS_MAX = {NBA_ML_HOME_ODDS_RANGE[1]}\n")
            f.write(f"NBA_ML_AWAY_ODDS_MIN = {NBA_ML_AWAY_ODDS_RANGE[0]}\n")
            f.write(f"NBA_ML_AWAY_ODDS_MAX = {NBA_ML_AWAY_ODDS_RANGE[1]}\n")
            f.write(f"NCAAB_ML_HOME_ODDS_MIN = {NCAAB_ML_HOME_ODDS_RANGE[0]}\n")
            f.write(f"NCAAB_ML_HOME_ODDS_MAX = {NCAAB_ML_HOME_ODDS_RANGE[1]}\n")
            f.write(f"NCAAB_ML_AWAY_ODDS_MIN = {NCAAB_ML_AWAY_ODDS_RANGE[0]}\n")
            f.write(f"NCAAB_ML_AWAY_ODDS_MAX = {NCAAB_ML_AWAY_ODDS_RANGE[1]}\n")

        shutil.rmtree("docs/win/basketball/model_testing/graded", ignore_errors=True)
        OPTIMIZER_STATS.unlink(missing_ok=True)

        for script in BASE_PIPELINE:
            subprocess.run(["python", script], check=True)

        for script in RULE_PIPELINE:
            subprocess.run(["python", script], check=True)

        row = {
            "RUN_DATE": RUN_DATE,
            "EDGE_MAX": EDGE_MAX,
            "SPREAD_MAX": SPREAD_MAX,
            "TOTAL_MIN": TOTAL_MIN,
            "NBA_TOTAL_STD": NBA_TOTAL_STD,
            "NBA_SPREAD_STD": NBA_SPREAD_STD,
            "NCAAB_TOTAL_STD": NCAAB_TOTAL_STD,
            "NCAAB_SPREAD_STD": NCAAB_SPREAD_STD,
            "NBA_TOTAL_EDGE": NBA_TOTAL_EDGE,
            "NBA_SPREAD_EDGE": NBA_SPREAD_EDGE,
            "NBA_ML_HOME_EDGE": NBA_ML_HOME_EDGE,
            "NBA_ML_AWAY_EDGE": NBA_ML_AWAY_EDGE,
            "NCAAB_TOTAL_EDGE": NCAAB_TOTAL_EDGE,
            "NCAAB_SPREAD_EDGE": NCAAB_SPREAD_EDGE,
            "NCAAB_ML_HOME_EDGE": NCAAB_ML_HOME_EDGE,
            "NCAAB_ML_AWAY_EDGE": NCAAB_ML_AWAY_EDGE,
            "NBA_TOTAL_EDGE_MIN": NBA_TOTAL_EDGE_MIN,
            "NCAAB_TOTAL_EDGE_MIN": NCAAB_TOTAL_EDGE_MIN,
            "NBA_SPREAD_EDGE_MIN": NBA_SPREAD_EDGE_MIN,
            "NCAAB_SPREAD_EDGE_MIN": NCAAB_SPREAD_EDGE_MIN,
            "NBA_ML_HOME_EDGE_MIN": NBA_ML_HOME_EDGE_MIN,
            "NBA_ML_AWAY_EDGE_MIN": NBA_ML_AWAY_EDGE_MIN,
            "NCAAB_ML_HOME_EDGE_MIN": NCAAB_ML_HOME_EDGE_MIN,
            "NCAAB_ML_AWAY_EDGE_MIN": NCAAB_ML_AWAY_EDGE_MIN,
            "NBA_ML_HOME_ODDS_MIN": NBA_ML_HOME_ODDS_RANGE[0],
            "NBA_ML_HOME_ODDS_MAX": NBA_ML_HOME_ODDS_RANGE[1],
            "NBA_ML_AWAY_ODDS_MIN": NBA_ML_AWAY_ODDS_RANGE[0],
            "NBA_ML_AWAY_ODDS_MAX": NBA_ML_AWAY_ODDS_RANGE[1],
            "NCAAB_ML_HOME_ODDS_MIN": NCAAB_ML_HOME_ODDS_RANGE[0],
            "NCAAB_ML_HOME_ODDS_MAX": NCAAB_ML_HOME_ODDS_RANGE[1],
            "NCAAB_ML_AWAY_ODDS_MIN": NCAAB_ML_AWAY_ODDS_RANGE[0],
            "NCAAB_ML_AWAY_ODDS_MAX": NCAAB_ML_AWAY_ODDS_RANGE[1],
        }

        if OPTIMIZER_STATS.exists():
            opt = pd.read_csv(OPTIMIZER_STATS)
            if not opt.empty:
                row.update(opt.iloc[0].to_dict())

        if NBA_STATS.exists():
            nba = pd.read_csv(NBA_STATS)
            if not nba.empty:
                nba_row = nba.iloc[0].to_dict()
                for k, v in nba_row.items():
                    if k != "LEAGUE":
                        row[f"NBA_{k}"] = v

        if NCAAB_STATS.exists():
            ncaab = pd.read_csv(NCAAB_STATS)
            if not ncaab.empty:
                ncaab_row = ncaab.iloc[0].to_dict()
                for k, v in ncaab_row.items():
                    if k != "LEAGUE":
                        row[f"NCAAB_{k}"] = v

        results.append(row)

df = pd.DataFrame(results)

sort_cols = [c for c in [
    "NBA_ML_HOME_WIN_PCT",
    "NCAAB_ML_HOME_WIN_PCT",
    "NBA_TOTAL_WIN_PCT",
    "NCAAB_TOTAL_WIN_PCT"
] if c in df.columns]

if sort_cols:
    df = df.sort_values(sort_cols, ascending=False)

df.to_csv(OUTPUT, index=False)

print("\nRule optimization complete")
print("Results saved:", OUTPUT)
