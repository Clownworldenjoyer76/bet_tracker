#!/usr/bin/env python3

# docs/win/baseball/scripts/01_merge/build_juice_files.py

import glob
import math
import sys
import traceback
from pathlib import Path
from datetime import datetime, UTC

import pandas as pd
from scipy.stats import poisson, skellam

INPUT_DIR = Path("docs/win/baseball/01_merge")
OUTPUT_DIR = INPUT_DIR / "01_merguiced"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = Path("docs/win/baseball/errors/01_merge")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG = ERROR_DIR / "build_juice_files.txt"

MONEYLINE_REQUIRED_COLUMNS = [
    "game_id", "sport", "league", "game_date", "game_time",
    "home_team", "away_team",
    "away_run_line", "home_run_line", "total",
    "away_dk_moneyline_american", "home_dk_moneyline_american",
    "away_dk_moneyline_decimal", "home_dk_moneyline_decimal",
    "home_pitcher", "away_pitcher",
    "home_prob", "away_prob",
    "away_projected_runs", "home_projected_runs", "total_projected_runs",
]

RUN_LINE_REQUIRED_COLUMNS = [
    "game_id", "sport", "league", "game_date", "game_time",
    "home_team", "away_team",
    "away_run_line", "home_run_line", "total",
    "away_dk_run_line_american", "home_dk_run_line_american",
    "away_dk_run_line_decimal", "home_dk_run_line_decimal",
    "home_pitcher", "away_pitcher",
    "home_prob", "away_prob",
    "away_projected_runs", "home_projected_runs", "total_projected_runs",
    "home_run_line_prob", "away_run_line_prob",
]

TOTAL_REQUIRED_COLUMNS = [
    "game_id", "sport", "league", "game_date", "game_time",
    "home_team", "away_team",
    "away_run_line", "home_run_line", "total",
    "dk_total_over_american", "dk_total_under_american",
    "dk_total_over_decimal", "dk_total_under_decimal",
    "home_pitcher", "away_pitcher",
    "home_prob", "away_prob",
    "away_projected_runs", "home_projected_runs", "total_projected_runs",
    "total_runs_over_prob", "total_runs_under_prob",
]


def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(UTC).isoformat()} | {msg}\n")


def american_to_decimal(odds):
    try:
        if pd.isna(odds):
            return None

        odds = float(odds)

        if odds == 0:
            return None

        if odds > 0:
            return 1 + (odds / 100)
        return 1 + (100 / abs(odds))
    except Exception:
        return None


def parse_slate_date_and_market(file_path: str):
    stem = Path(file_path).stem

    if stem.endswith("_mlb_moneyline"):
        return stem.replace("_mlb_moneyline", ""), "moneyline"

    if stem.endswith("_mlb_run_line"):
        return stem.replace("_mlb_run_line", ""), "run_line"

    if stem.endswith("_mlb_total"):
        return stem.replace("_mlb_total", ""), "total"

    return None, None


def validate_schema(df: pd.DataFrame, required_columns: list[str], file_path: str) -> bool:
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        log(f"SCHEMA ERROR: {file_path} missing columns: {missing_cols}")
        return False
    return True


def coerce_numeric(df: pd.DataFrame, cols: list[str]):
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")


def process_moneyline(file_path: str):
    df = pd.read_csv(file_path)

    if df.empty:
        log(f"NO OUTPUT: {file_path} is empty — skipping juice")
        return

    if not validate_schema(df, MONEYLINE_REQUIRED_COLUMNS, file_path):
        return

    coerce_numeric(
        df,
        [
            "home_prob", "away_prob",
            "home_projected_runs", "away_projected_runs", "total_projected_runs",
            "away_run_line", "home_run_line", "total",
            "away_dk_moneyline_american", "home_dk_moneyline_american",
            "away_dk_moneyline_decimal", "home_dk_moneyline_decimal",
        ],
    )

    for i, r in df.iterrows():
        if pd.isna(r["home_prob"]) or pd.isna(r["away_prob"]):
            log(f"ROW ISSUE: {file_path} idx={i} bad probs")

    ml = df.copy()

    ml["away_dk_decimal_moneyline"] = ml["away_dk_moneyline_american"].apply(american_to_decimal)
    ml["home_dk_decimal_moneyline"] = ml["home_dk_moneyline_american"].apply(american_to_decimal)

    ml["away_fair_decimal_moneyline"] = ml["away_prob"].apply(
        lambda x: 1 / x if pd.notna(x) and x > 0 else None
    )
    ml["home_fair_decimal_moneyline"] = ml["home_prob"].apply(
        lambda x: 1 / x if pd.notna(x) and x > 0 else None
    )

    slate_date, market = parse_slate_date_and_market(file_path)
    if not slate_date or market != "moneyline":
        log(f"FILENAME ERROR: could not parse market/date from {file_path}")
        return

    output_path = OUTPUT_DIR / f"{slate_date}_mlb_moneyline.csv"
    ml.to_csv(output_path, index=False)
    log(f"Processed: {file_path} -> {output_path}")


def process_total(file_path: str):
    df = pd.read_csv(file_path)

    if df.empty:
        log(f"NO OUTPUT: {file_path} is empty — skipping juice")
        return

    if not validate_schema(df, TOTAL_REQUIRED_COLUMNS, file_path):
        return

    coerce_numeric(
        df,
        [
            "home_prob", "away_prob",
            "home_projected_runs", "away_projected_runs", "total_projected_runs",
            "away_run_line", "home_run_line", "total",
            "dk_total_over_american", "dk_total_under_american",
            "dk_total_over_decimal", "dk_total_under_decimal",
            "total_runs_over_prob", "total_runs_under_prob",
        ],
    )

    for i, r in df.iterrows():
        if pd.isna(r["total_projected_runs"]) or pd.isna(r["total"]):
            log(f"ROW ISSUE: {file_path} idx={i} bad total inputs")

    tot = df.copy()

    tot["dk_total_over_decimal"] = tot["dk_total_over_american"].apply(american_to_decimal)
    tot["dk_total_under_decimal"] = tot["dk_total_under_american"].apply(american_to_decimal)

    over = []
    under = []

    for i, r in tot.iterrows():
        lam = r["total_projected_runs"]
        total_line = r["total"]

        if pd.isna(lam) or pd.isna(total_line) or lam <= 0:
            log(f"ROW ISSUE: {file_path} idx={i} bad total inputs")
            over.append(None)
            under.append(None)
            continue

        if total_line % 1 == 0:
            log(
                f"WHOLE NUMBER TOTAL: {file_path} idx={i} total={total_line} — "
                f"push not modelled; skipping row"
            )
            over.append(None)
            under.append(None)
            continue

        k = math.floor(total_line)
        p_under = poisson.cdf(k, lam)
        p_over = 1 - p_under

        under.append(1 / p_under if p_under > 0 else None)
        over.append(1 / p_over if p_over > 0 else None)

    tot["fair_total_over_decimal"] = over
    tot["fair_total_under_decimal"] = under

    slate_date, market = parse_slate_date_and_market(file_path)
    if not slate_date or market != "total":
        log(f"FILENAME ERROR: could not parse market/date from {file_path}")
        return

    output_path = OUTPUT_DIR / f"{slate_date}_mlb_total.csv"
    tot.to_csv(output_path, index=False)
    log(f"Processed: {file_path} -> {output_path}")


def process_run_line(file_path: str):
    df = pd.read_csv(file_path)

    if df.empty:
        log(f"NO OUTPUT: {file_path} is empty — skipping juice")
        return

    if not validate_schema(df, RUN_LINE_REQUIRED_COLUMNS, file_path):
        return

    coerce_numeric(
        df,
        [
            "home_prob", "away_prob",
            "home_projected_runs", "away_projected_runs", "total_projected_runs",
            "away_run_line", "home_run_line", "total",
            "away_dk_run_line_american", "home_dk_run_line_american",
            "away_dk_run_line_decimal", "home_dk_run_line_decimal",
            "home_run_line_prob", "away_run_line_prob",
        ],
    )

    for i, r in df.iterrows():
        if pd.isna(r["home_projected_runs"]) or pd.isna(r["away_projected_runs"]):
            log(f"ROW ISSUE: {file_path} idx={i} run line invalid lambdas")

    rl = df.copy()

    rl["home_dk_run_line_decimal"] = rl["home_dk_run_line_american"].apply(american_to_decimal)
    rl["away_dk_run_line_decimal"] = rl["away_dk_run_line_american"].apply(american_to_decimal)

    home_vals = []
    away_vals = []
    home_probs = []
    away_probs = []

    for i, r in rl.iterrows():
        lambda_home = r["home_projected_runs"]
        lambda_away = r["away_projected_runs"]

        if pd.isna(lambda_home) or pd.isna(lambda_away) or lambda_home <= 0 or lambda_away <= 0:
            log(f"ROW ISSUE: {file_path} idx={i} run line invalid lambdas")
            home_vals.append(None)
            away_vals.append(None)
            home_probs.append(None)
            away_probs.append(None)
            continue

        home_line = r["home_run_line"]
        away_line = r["away_run_line"]

        if pd.isna(home_line) or pd.isna(away_line):
            log(f"ROW ISSUE: {file_path} idx={i} missing run lines")
            home_vals.append(None)
            away_vals.append(None)
            home_probs.append(None)
            away_probs.append(None)
            continue

        if home_line == -1.5:
            p_home = 1 - skellam.cdf(1, lambda_home, lambda_away)
            p_away = 1 - p_home
        elif away_line == -1.5:
            p_away = 1 - skellam.cdf(1, lambda_away, lambda_home)
            p_home = 1 - p_away
        else:
            log(
                f"ROW ISSUE: {file_path} idx={i} unexpected run lines: "
                f"home={home_line} away={away_line}"
            )
            home_vals.append(None)
            away_vals.append(None)
            home_probs.append(None)
            away_probs.append(None)
            continue

        p_home = min(max(p_home, 0.01), 0.99)
        p_away = min(max(p_away, 0.01), 0.99)

        home_probs.append(p_home)
        away_probs.append(p_away)

        home_vals.append(1 / p_home)
        away_vals.append(1 / p_away)

    rl["home_fair_run_line_decimal"] = home_vals
    rl["away_fair_run_line_decimal"] = away_vals
    rl["home_prob_run_line"] = home_probs
    rl["away_prob_run_line"] = away_probs

    slate_date, market = parse_slate_date_and_market(file_path)
    if not slate_date or market != "run_line":
        log(f"FILENAME ERROR: could not parse market/date from {file_path}")
        return

    output_path = OUTPUT_DIR / f"{slate_date}_mlb_run_line.csv"
    rl.to_csv(output_path, index=False)
    log(f"Processed: {file_path} -> {output_path}")


def main():
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(f"{datetime.now(UTC).isoformat()}\n")

    try:
        moneyline_files = glob.glob(str(INPUT_DIR / "*_mlb_moneyline.csv"))
        run_line_files = glob.glob(str(INPUT_DIR / "*_mlb_run_line.csv"))
        total_files = glob.glob(str(INPUT_DIR / "*_mlb_total.csv"))

        for file_path in sorted(moneyline_files):
            process_moneyline(file_path)

        for file_path in sorted(run_line_files):
            process_run_line(file_path)

        for file_path in sorted(total_files):
            process_total(file_path)

        log("Completed successfully.")

    except Exception as e:
        traceback.print_exc()
        log(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
