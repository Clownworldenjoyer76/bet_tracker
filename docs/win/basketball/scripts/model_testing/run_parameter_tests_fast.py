#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/run_parameter_tests_fast.py

import itertools
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


RUN_DATES = [
    "2026_02_24",
    "2026_02_26",
    "2026_02_27",
    "2026_03_01",
    "2026_03_02",
    "2026_03_03",
    "2026_03_04",
    "2026_03_05",
    "2026_03_06",
]


NBA_TOTAL_STD_VALUES = [10, 11, 12, 13, 14, 15, 16, 17]
NBA_SPREAD_STD_VALUES = [10, 11, 12, 13, 14, 15, 16]
NCAAB_TOTAL_STD_VALUES = [8, 9, 10, 11, 12, 13, 14]
NCAAB_SPREAD_STD_VALUES = [10, 11, 12, 13, 14, 15]

EDGE_MIN_VALUES = [0.04, 0.05, 0.06, 0.08]
EDGE_MAX_VALUES = [0.20, 0.25]
SPREAD_MAX_VALUES = [15, 20]
NBA_TOTAL_MIN_DIFF_VALUES = [1.5, 2.0, 2.5]
NBA_TOTAL_LINE_MAX_VALUES = [235, 240]
NCAAB_TOTAL_MIN_VALUES = [135, 140]
NCAAB_ML_LOW_VALUES = [-200, -180, -160]
NCAAB_ML_HIGH_VALUES = [-150, -140]
NCAAB_ML_MIN_PROB_VALUES = [0.55, 0.58]


MAX_RUNS = 2000
MIN_COMBINED_SAMPLE = 60
RANDOM_SEED = 42

MAX_WORKERS = max(1, (os.cpu_count() or 4) - 1)

PRINT_EVERY = 200
TOP_N = 50


DATA_FILE = Path(
    "docs/win/basketball/model_testing/optimizer_base_dataset.csv"
)

OUTPUT = Path(
    "docs/win/basketball/model_testing/rule_test_results_fast.csv"
)

LEADERBOARD = Path(
    "docs/win/basketball/model_testing/rule_test_leaderboard_fast.csv"
)


WORKER_DF = None


def build_grid():

    combos = itertools.product(
        NBA_TOTAL_STD_VALUES,
        NBA_SPREAD_STD_VALUES,
        NCAAB_TOTAL_STD_VALUES,
        NCAAB_SPREAD_STD_VALUES,
        EDGE_MIN_VALUES,
        EDGE_MAX_VALUES,
        SPREAD_MAX_VALUES,
        NBA_TOTAL_MIN_DIFF_VALUES,
        NBA_TOTAL_LINE_MAX_VALUES,
        NCAAB_TOTAL_MIN_VALUES,
        NCAAB_ML_LOW_VALUES,
        NCAAB_ML_HIGH_VALUES,
        NCAAB_ML_MIN_PROB_VALUES,
    )

    grid = []

    for combo in combos:

        if combo[4] >= combo[5]:
            continue

        if combo[10] >= combo[11]:
            continue

        grid.append(combo)

    random.seed(RANDOM_SEED)

    if len(grid) > MAX_RUNS:
        grid = random.sample(grid, MAX_RUNS)

    return grid


def roi(df):

    if df.empty:
        return 0

    odds = pd.to_numeric(df["take_odds"], errors="coerce").fillna(-110)
    results = df["bet_result"].astype(str)

    wins = results == "Win"
    losses = results == "Loss"

    profit = pd.Series(0.0, index=df.index)

    profit.loc[wins & (odds > 0)] = odds[wins & (odds > 0)] / 100
    profit.loc[wins & (odds < 0)] = 100 / odds[wins & (odds < 0)].abs()

    profit.loc[losses] = -1

    return profit.sum() / len(df)


def win_pct(df):

    if df.empty:
        return 0

    return (df["bet_result"] == "Win").mean()


def add_metrics(row, prefix, df):

    ml_home = df[(df.market_type == "moneyline") & (df.bet_side == "home")]
    ml_away = df[(df.market_type == "moneyline") & (df.bet_side == "away")]

    totals = df[df.market_type == "total"]
    spreads = df[df.market_type == "spread"]

    sections = {
        f"{prefix}_ML_HOME": ml_home,
        f"{prefix}_ML_AWAY": ml_away,
        f"{prefix}_TOTAL": totals,
        f"{prefix}_SPREAD": spreads,
        f"{prefix}_ALL": df,
    }

    for name, section in sections.items():

        row[f"{name}_SAMPLE"] = len(section)
        row[f"{name}_WIN_PCT"] = win_pct(section)
        row[f"{name}_ROI"] = roi(section)

    row[f"{prefix}_COMBINED_SAMPLE"] = len(totals) + len(spreads)


def calc_score(row):

    nba_sample = row.get("NBA_COMBINED_SAMPLE", 0)
    ncaab_sample = row.get("NCAAB_COMBINED_SAMPLE", 0)

    total = nba_sample + ncaab_sample

    if total == 0:
        return 0

    nba_roi = row.get("NBA_ALL_ROI", 0)
    ncaab_roi = row.get("NCAAB_ALL_ROI", 0)

    weighted_roi = ((nba_roi * nba_sample) + (ncaab_roi * ncaab_sample)) / total

    return weighted_roi * math.sqrt(total)


def init_worker(df):

    global WORKER_DF
    WORKER_DF = df


def evaluate_task(task):

    global WORKER_DF

    run_index, total_runs, run_date, params = task

    df = WORKER_DF

    df = df[df.game_date == run_date]

    edge_min = params[4]
    edge_max = params[5]

    df = df[(df.candidate_edge >= edge_min) & (df.candidate_edge <= edge_max)]

    if df.empty:
        return None

    nba = df[df.market == "NBA"]
    ncaab = df[df.market == "NCAAB"]

    row = {
        "RUN_DATE": run_date,
        "PARAMS": params
    }

    add_metrics(row, "NBA", nba)
    add_metrics(row, "NCAAB", ncaab)

    combined = row.get("NBA_COMBINED_SAMPLE", 0) + row.get("NCAAB_COMBINED_SAMPLE", 0)

    if combined < MIN_COMBINED_SAMPLE:
        return None

    row["COMBINED_SAMPLE"] = combined
    row["SCORE"] = calc_score(row)

    return row


def main():

    if not DATA_FILE.exists():
        raise FileNotFoundError(DATA_FILE)

    df = pd.read_csv(DATA_FILE)

    grid = build_grid()

    tasks = []

    total_runs = len(grid) * len(RUN_DATES)

    run_index = 0

    for date in RUN_DATES:

        for params in grid:

            run_index += 1
            tasks.append((run_index, total_runs, date, params))

    print("Rows loaded:", len(df))
    print("Grid size:", len(grid))
    print("Total evaluations:", total_runs)
    print("Workers:", MAX_WORKERS)

    results = []

    start = time.time()

    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=init_worker,
        initargs=(df,)
    ) as executor:

        futures = [executor.submit(evaluate_task, t) for t in tasks]

        for i, future in enumerate(as_completed(futures), 1):

            r = future.result()

            if r:
                results.append(r)

            if i % PRINT_EVERY == 0:

                elapsed = time.time() - start
                rate = i / elapsed

                remaining = total_runs - i
                eta = remaining / rate

                print(
                    f"{i}/{total_runs}  rate={rate:.1f}/sec  eta={eta:.1f}s"
                )

    df = pd.DataFrame(results)

    df = df.sort_values("SCORE", ascending=False)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT, index=False)

    df.head(TOP_N).to_csv(LEADERBOARD, index=False)

    print("Done.")
    print("Results:", OUTPUT)
    print("Leaderboard:", LEADERBOARD)


if __name__ == "__main__":
    main()
