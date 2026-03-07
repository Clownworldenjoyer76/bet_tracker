#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/run_parameter_tests_fast.py

import itertools
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

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
TOP_N = 50
PRINT_EVERY = 100
CHECKPOINT_EVERY = 250
MAX_WORKERS = max(1, (os.cpu_count() or 4) - 1)

DATA_FILE = Path("docs/win/basketball/model_testing/optimizer_base_dataset.csv")
OUTPUT = Path("docs/win/basketball/model_testing/rule_test_results_fast.csv")
LEADERBOARD = Path("docs/win/basketball/model_testing/rule_test_leaderboard_fast.csv")

# Global dataset inside workers
WORKER_DF = None


def build_grid() -> list[tuple]:
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
        edge_min = combo[4]
        edge_max = combo[5]
        ml_low = combo[10]
        ml_high = combo[11]

        if edge_min >= edge_max:
            continue
        if ml_low >= ml_high:
            continue

        grid.append(combo)

    random.seed(RANDOM_SEED)
    if len(grid) > MAX_RUNS:
        grid = random.sample(grid, MAX_RUNS)

    return grid


def american_roi(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0

    odds = pd.to_numeric(df["take_odds"], errors="coerce").fillna(-110)
    result = df["bet_result"].astype(str).str.strip()

    wins = result.eq("Win")
    losses = result.eq("Loss")

    profit = pd.Series(0.0, index=df.index)

    pos = odds > 0
    neg = odds < 0

    profit.loc[wins & pos] = odds.loc[wins & pos] / 100.0
    profit.loc[wins & neg] = 100.0 / odds.loc[wins & neg].abs()
    profit.loc[losses] = -1.0

    return float(profit.sum()) / len(df)


def win_pct(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(df["bet_result"].astype(str).str.strip().eq("Win").mean())


def add_metrics(row: dict[str, Any], prefix: str, df: pd.DataFrame) -> None:
    ml_home = df[(df["market_type"] == "moneyline") & (df["bet_side"] == "home")]
    ml_away = df[(df["market_type"] == "moneyline") & (df["bet_side"] == "away")]

    total = df[df["market_type"] == "total"]
    total_over = df[(df["market_type"] == "total") & (df["bet_side"] == "over")]
    total_under = df[(df["market_type"] == "total") & (df["bet_side"] == "under")]

    spread = df[df["market_type"] == "spread"]
    spread_home = df[(df["market_type"] == "spread") & (df["bet_side"] == "home")]
    spread_away = df[(df["market_type"] == "spread") & (df["bet_side"] == "away")]

    sections = {
        f"{prefix}_ML_HOME": ml_home,
        f"{prefix}_ML_AWAY": ml_away,
        f"{prefix}_TOTAL": total,
        f"{prefix}_TOTAL_OVER": total_over,
        f"{prefix}_TOTAL_UNDER": total_under,
        f"{prefix}_SPREAD": spread,
        f"{prefix}_SPREAD_HOME": spread_home,
        f"{prefix}_SPREAD_AWAY": spread_away,
        f"{prefix}_ALL": df,
    }

    for name, section in sections.items():
        row[f"{name}_SAMPLE"] = len(section)
        row[f"{name}_WIN_PCT"] = win_pct(section)
        row[f"{name}_ROI"] = american_roi(section)
        row[f"{name}_AVG_EDGE"] = (
            float(pd.to_numeric(section["candidate_edge"], errors="coerce").mean())
            if "candidate_edge" in section.columns and not section.empty
            else 0.0
        )

    row[f"{prefix}_COMBINED_SAMPLE"] = len(total) + len(spread)


def calc_score(row: dict[str, Any]) -> float:
    nba_sample = float(row.get("NBA_COMBINED_SAMPLE", 0) or 0)
    ncaab_sample = float(row.get("NCAAB_COMBINED_SAMPLE", 0) or 0)
    total_sample = nba_sample + ncaab_sample

    nba_roi = float(row.get("NBA_ALL_ROI", 0) or 0)
    ncaab_roi = float(row.get("NCAAB_ALL_ROI", 0) or 0)

    if total_sample <= 0:
        return 0.0

    weighted_roi = ((nba_roi * nba_sample) + (ncaab_roi * ncaab_sample)) / total_sample
    return weighted_roi * math.sqrt(total_sample)


def init_worker(df: pd.DataFrame) -> None:
    global WORKER_DF
    WORKER_DF = df


def apply_param_filters(df: pd.DataFrame, run_date: str, params: tuple) -> pd.DataFrame:
    (
        nba_total_std,
        nba_spread_std,
        ncaab_total_std,
        ncaab_spread_std,
        edge_min,
        edge_max,
        spread_max,
        nba_total_min_diff,
        nba_total_line_max,
        ncaab_total_min,
        ncaab_ml_low,
        ncaab_ml_high,
        ncaab_ml_min_prob,
    ) = params

    work = df[df["game_date"] == run_date].copy()
    if work.empty:
        return work

    work["candidate_edge"] = pd.to_numeric(work["candidate_edge"], errors="coerce").fillna(0.0)
    work["take_odds"] = pd.to_numeric(work["take_odds"], errors="coerce").fillna(-110)
    work["line_value"] = pd.to_numeric(work.get("line_value", 0), errors="coerce").fillna(0.0)
    work["model_total"] = pd.to_numeric(work.get("model_total", 0), errors="coerce").fillna(0.0)
    work["book_total"] = pd.to_numeric(work.get("book_total", 0), errors="coerce").fillna(0.0)
    work["model_prob"] = pd.to_numeric(work.get("model_prob", 0), errors="coerce").fillna(0.0)

    mask = work["candidate_edge"].between(edge_min, edge_max)

    # Spread max
    spread_mask = (
        (work["market_type"] != "spread")
        | (work["line_value"].abs() <= spread_max)
    )
    mask &= spread_mask

    # NBA totals rule
    nba_total_mask = (
        (work["market"] != "NBA")
        | (work["market_type"] != "total")
        | (
            (work["book_total"] <= nba_total_line_max)
            & ((work["model_total"] - work["book_total"]).abs() >= nba_total_min_diff)
        )
    )
    mask &= nba_total_mask

    # NCAAB totals rule
    ncaab_total_mask = (
        (work["market"] != "NCAAB")
        | (work["market_type"] != "total")
        | (work["book_total"] >= ncaab_total_min)
    )
    mask &= ncaab_total_mask

    # NCAAB moneyline rule
    ncaab_ml_mask = (
        (work["market"] != "NCAAB")
        | (work["market_type"] != "moneyline")
        | (
            work["take_odds"].between(ncaab_ml_low, ncaab_ml_high)
            & (work["model_prob"] >= ncaab_ml_min_prob)
        )
    )
    mask &= ncaab_ml_mask

    filtered = work[mask].copy()

    if filtered.empty:
        return filtered

    # keep best bet per game/market bucket
    sort_cols = ["candidate_edge"]
    filtered = filtered.sort_values(sort_cols, ascending=False)

    dedupe_cols = ["game_date", "away_team", "home_team", "market_type"]
    existing = [c for c in dedupe_cols if c in filtered.columns]
    if existing:
        filtered = filtered.drop_duplicates(subset=existing, keep="first")

    return filtered


def evaluate_task(task: tuple[int, int, str, tuple]) -> dict[str, Any]:
    global WORKER_DF

    run_index, total_runs, run_date, params = task
    started = time.time()

    filtered = apply_param_filters(WORKER_DF, run_date, params)

    row: dict[str, Any] = {
        "RUN_INDEX": run_index,
        "TOTAL_RUNS": total_runs,
        "RUN_DATE": run_date,
        "NBA_TOTAL_STD": params[0],
        "NBA_SPREAD_STD": params[1],
        "NCAAB_TOTAL_STD": params[2],
        "NCAAB_SPREAD_STD": params[3],
        "EDGE_MIN": params[4],
        "EDGE_MAX": params[5],
        "SPREAD_MAX": params[6],
        "NBA_TOTAL_MIN_DIFF": params[7],
        "NBA_TOTAL_LINE_MAX": params[8],
        "NCAAB_TOTAL_MIN": params[9],
        "NCAAB_ML_LOW": params[10],
        "NCAAB_ML_HIGH": params[11],
        "NCAAB_ML_MIN_PROB": params[12],
        "ELAPSED_SEC": round(time.time() - started, 4),
    }

    if filtered.empty:
        row["STATUS"] = "below_min_sample"
        row["COMBINED_SAMPLE"] = 0
        row["SCORE"] = 0.0
        return row

    nba = filtered[filtered["market"] == "NBA"].copy()
    ncaab = filtered[filtered["market"] == "NCAAB"].copy()

    add_metrics(row, "NBA", nba)
    add_metrics(row, "NCAAB", ncaab)

    combined_sample = int(row.get("NBA_COMBINED_SAMPLE", 0) or 0) + int(row.get("NCAAB_COMBINED_SAMPLE", 0) or 0)
    row["COMBINED_SAMPLE"] = combined_sample
    row["SCORE"] = calc_score(row)

    if combined_sample < MIN_COMBINED_SAMPLE:
        row["STATUS"] = "below_min_sample"
    else:
        row["STATUS"] = "ok"

    return row


def build_tasks(grid: list[tuple]) -> list[tuple[int, int, str, tuple]]:
    tasks = []
    total_runs = len(RUN_DATES) * len(grid)

    run_index = 0
    for run_date in RUN_DATES:
        for params in grid:
            run_index += 1
            tasks.append((run_index, total_runs, run_date, params))

    return tasks


def save_outputs(results: list[dict[str, Any]]) -> None:
    if not results:
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(results).sort_values(
        ["SCORE", "COMBINED_SAMPLE"], ascending=[False, False]
    )
    df.to_csv(OUTPUT, index=False)
    df.head(TOP_N).to_csv(LEADERBOARD, index=False)


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing base dataset: {DATA_FILE}")

    started = time.time()

    df = pd.read_csv(DATA_FILE, low_memory=False)
    grid = build_grid()
    tasks = build_tasks(grid)

    print(f"Base rows: {len(df):,}")
    print(f"Grid size: {len(grid):,}")
    print(f"Total evaluations: {len(tasks):,}")
    print(f"Workers: {MAX_WORKERS}")
    print("Starting fast in-memory optimization...", flush=True)

    results: list[dict[str, Any]] = []
    completed = 0
    kept = 0

    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=init_worker,
        initargs=(df,),
    ) as executor:
        futures = [executor.submit(evaluate_task, task) for task in tasks]

        for future in as_completed(futures):
            row = future.result()
            completed += 1

            if row.get("STATUS") == "ok":
                kept += 1
                results.append(row)

            if completed % PRINT_EVERY == 0 or completed == len(tasks):
                elapsed = time.time() - started
                rate = completed / elapsed if elapsed > 0 else 0.0
                remaining = len(tasks) - completed
                eta_sec = remaining / rate if rate > 0 else 0.0

                print(
                    f"Completed: {completed}/{len(tasks)} | "
                    f"kept: {kept} | rate: {rate:.1f}/sec | eta: {eta_sec:.1f}s",
                    flush=True,
                )

                if results:
                    best = max(results, key=lambda x: x.get("SCORE", 0))
                    print(
                        f"Best so far | date={best['RUN_DATE']} | "
                        f"sample={best.get('COMBINED_SAMPLE', 0)} | "
                        f"score={best.get('SCORE', 0):.3f} | "
                        f"nba_roi={best.get('NBA_ALL_ROI', 0):.3f} | "
                        f"ncaab_roi={best.get('NCAAB_ALL_ROI', 0):.3f}",
                        flush=True,
                    )

            if completed % CHECKPOINT_EVERY == 0 or completed == len(tasks):
                save_outputs(results)

    save_outputs(results)

    elapsed = time.time() - started
    print(f"Done in {elapsed:.2f}s")
    print(f"Saved: {OUTPUT}")
    print(f"Saved leaderboard: {LEADERBOARD}")


if __name__ == "__main__":
    main()