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

INPUT_DIR  = Path("docs/win/baseball/01_merge")
OUTPUT_DIR = INPUT_DIR / "01_merguiced"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = Path("docs/win/baseball/errors/01_merge")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "build_juice_files.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== build_juice_files RUN {datetime.now(UTC).isoformat()} ===\n")

MONEYLINE_REQUIRED_COLUMNS = [
    "game_id","sport","league","game_date","game_time","home_team","away_team",
    "away_run_line","home_run_line","total",
    "away_dk_moneyline_american","home_dk_moneyline_american",
    "away_dk_moneyline_decimal","home_dk_moneyline_decimal",
    "home_pitcher","away_pitcher","home_prob","away_prob",
    "away_projected_runs","home_projected_runs","total_projected_runs",
]

RUN_LINE_REQUIRED_COLUMNS = [
    "game_id","sport","league","game_date","game_time","home_team","away_team",
    "away_run_line","home_run_line","total",
    "away_dk_run_line_american","home_dk_run_line_american",
    "away_dk_run_line_decimal","home_dk_run_line_decimal",
    "home_pitcher","away_pitcher","home_prob","away_prob",
    "away_projected_runs","home_projected_runs","total_projected_runs",
    "home_run_line_prob","away_run_line_prob",
]

TOTAL_REQUIRED_COLUMNS = [
    "game_id","sport","league","game_date","game_time","home_team","away_team",
    "away_run_line","home_run_line","total",
    "dk_total_over_american","dk_total_under_american",
    "dk_total_over_decimal","dk_total_under_decimal",
    "home_pitcher","away_pitcher","home_prob","away_prob",
    "away_projected_runs","home_projected_runs","total_projected_runs",
    "total_runs_over_prob","total_runs_under_prob",
]


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
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


def validate_schema(df, required_columns, file_path):
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        log(f"SCHEMA ERROR: {file_path} missing columns: {missing_cols}")
        return False
    return True


def coerce_numeric(df, cols):
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")


def process_moneyline(file_path, summary):
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            log(f"EMPTY: {file_path} — skipping")
            summary["empty"] += 1
            return
        if not validate_schema(df, MONEYLINE_REQUIRED_COLUMNS, file_path):
            summary["schema_errors"] += 1
            return

        coerce_numeric(df, [
            "home_prob","away_prob",
            "home_projected_runs","away_projected_runs","total_projected_runs",
            "away_run_line","home_run_line","total",
            "away_dk_moneyline_american","home_dk_moneyline_american",
            "away_dk_moneyline_decimal","home_dk_moneyline_decimal",
        ])

        for i, r in df.iterrows():
            if pd.isna(r["home_prob"]) or pd.isna(r["away_prob"]):
                log(f"ROW ISSUE: {file_path} idx={i} bad probs")
                summary["row_issues"] += 1

        ml = df.copy()
        ml["away_dk_decimal_moneyline"]   = ml["away_dk_moneyline_american"].apply(american_to_decimal)
        ml["home_dk_decimal_moneyline"]   = ml["home_dk_moneyline_american"].apply(american_to_decimal)
        ml["away_fair_decimal_moneyline"] = ml["away_prob"].apply(lambda x: 1/x if pd.notna(x) and x > 0 else None)
        ml["home_fair_decimal_moneyline"] = ml["home_prob"].apply(lambda x: 1/x if pd.notna(x) and x > 0 else None)

        slate_date, market = parse_slate_date_and_market(file_path)
        if not slate_date or market != "moneyline":
            log(f"FILENAME ERROR: {file_path}")
            summary["errors"] += 1
            return

        out = OUTPUT_DIR / f"{slate_date}_mlb_moneyline.csv"
        ml.to_csv(out, index=False)
        log(f"WROTE {out} ({len(ml)} rows)")
        summary["files_written"] += 1
        summary["rows_written"]  += len(ml)

    except Exception as e:
        log(f"ERROR moneyline {file_path}: {e}\n{traceback.format_exc()}")
        summary["errors"] += 1


def process_total(file_path, summary):
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            log(f"EMPTY: {file_path} — skipping")
            summary["empty"] += 1
            return
        if not validate_schema(df, TOTAL_REQUIRED_COLUMNS, file_path):
            summary["schema_errors"] += 1
            return

        coerce_numeric(df, [
            "home_prob","away_prob",
            "home_projected_runs","away_projected_runs","total_projected_runs",
            "away_run_line","home_run_line","total",
            "dk_total_over_american","dk_total_under_american",
            "dk_total_over_decimal","dk_total_under_decimal",
            "total_runs_over_prob","total_runs_under_prob",
        ])

        tot = df.copy()
        tot["dk_total_over_decimal"]  = tot["dk_total_over_american"].apply(american_to_decimal)
        tot["dk_total_under_decimal"] = tot["dk_total_under_american"].apply(american_to_decimal)

        over  = []
        under = []

        for i, r in tot.iterrows():
            lam        = r["total_projected_runs"]
            total_line = r["total"]

            if pd.isna(lam) or pd.isna(total_line) or lam <= 0:
                log(f"ROW ISSUE: {file_path} idx={i} bad total inputs")
                summary["row_issues"] += 1
                over.append(None)
                under.append(None)
                continue

            if total_line % 1 == 0:
                log(f"WHOLE NUMBER TOTAL: {file_path} idx={i} total={total_line} — push not modelled; skipping row")
                summary["row_issues"] += 1
                over.append(None)
                under.append(None)
                continue

            k       = math.floor(total_line)
            p_under = poisson.cdf(k, lam)
            p_over  = 1 - p_under

            under.append(1 / p_under if p_under > 0 else None)
            over.append(1 / p_over   if p_over  > 0 else None)

        tot["fair_total_over_decimal"]  = over
        tot["fair_total_under_decimal"] = under

        slate_date, market = parse_slate_date_and_market(file_path)
        if not slate_date or market != "total":
            log(f"FILENAME ERROR: {file_path}")
            summary["errors"] += 1
            return

        out = OUTPUT_DIR / f"{slate_date}_mlb_total.csv"
        tot.to_csv(out, index=False)
        log(f"WROTE {out} ({len(tot)} rows)")
        summary["files_written"] += 1
        summary["rows_written"]  += len(tot)

    except Exception as e:
        log(f"ERROR total {file_path}: {e}\n{traceback.format_exc()}")
        summary["errors"] += 1


def process_run_line(file_path, summary):
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            log(f"EMPTY: {file_path} — skipping")
            summary["empty"] += 1
            return
        if not validate_schema(df, RUN_LINE_REQUIRED_COLUMNS, file_path):
            summary["schema_errors"] += 1
            return

        coerce_numeric(df, [
            "home_prob","away_prob",
            "home_projected_runs","away_projected_runs","total_projected_runs",
            "away_run_line","home_run_line","total",
            "away_dk_run_line_american","home_dk_run_line_american",
            "away_dk_run_line_decimal","home_dk_run_line_decimal",
            "home_run_line_prob","away_run_line_prob",
        ])

        rl = df.copy()
        rl["home_dk_run_line_decimal"] = rl["home_dk_run_line_american"].apply(american_to_decimal)
        rl["away_dk_run_line_decimal"] = rl["away_dk_run_line_american"].apply(american_to_decimal)

        home_vals  = []
        away_vals  = []
        home_probs = []
        away_probs = []

        for i, r in rl.iterrows():
            lambda_home = r["home_projected_runs"]
            lambda_away = r["away_projected_runs"]

            if pd.isna(lambda_home) or pd.isna(lambda_away) or lambda_home <= 0 or lambda_away <= 0:
                log(f"ROW ISSUE: {file_path} idx={i} run line invalid lambdas")
                summary["row_issues"] += 1
                home_vals.append(None); away_vals.append(None)
                home_probs.append(None); away_probs.append(None)
                continue

            home_line = r["home_run_line"]
            away_line = r["away_run_line"]

            if pd.isna(home_line) or pd.isna(away_line):
                log(f"ROW ISSUE: {file_path} idx={i} missing run lines")
                summary["row_issues"] += 1
                home_vals.append(None); away_vals.append(None)
                home_probs.append(None); away_probs.append(None)
                continue

            if home_line == -1.5:
                p_home = 1 - skellam.cdf(1, lambda_home, lambda_away)
                p_away = skellam.cdf(1, lambda_home, lambda_away)
            elif away_line == -1.5:
                p_away = 1 - skellam.cdf(1, lambda_away, lambda_home)
                p_home = skellam.cdf(1, lambda_away, lambda_home)
            else:
                log(f"ROW ISSUE: {file_path} idx={i} unexpected run lines: home={home_line} away={away_line}")
                summary["row_issues"] += 1
                home_vals.append(None); away_vals.append(None)
                home_probs.append(None); away_probs.append(None)
                continue

            p_home = min(max(p_home, 0.01), 0.99)
            p_away = min(max(p_away, 0.01), 0.99)

            home_probs.append(p_home); away_probs.append(p_away)
            home_vals.append(1 / p_home); away_vals.append(1 / p_away)

        rl["home_fair_run_line_decimal"] = home_vals
        rl["away_fair_run_line_decimal"] = away_vals
        rl["home_prob_run_line"]         = home_probs
        rl["away_prob_run_line"]         = away_probs

        slate_date, market = parse_slate_date_and_market(file_path)
        if not slate_date or market != "run_line":
            log(f"FILENAME ERROR: {file_path}")
            summary["errors"] += 1
            return

        out = OUTPUT_DIR / f"{slate_date}_mlb_run_line.csv"
        rl.to_csv(out, index=False)
        log(f"WROTE {out} ({len(rl)} rows)")
        summary["files_written"] += 1
        summary["rows_written"]  += len(rl)

    except Exception as e:
        log(f"ERROR run_line {file_path}: {e}\n{traceback.format_exc()}")
        summary["errors"] += 1


def main():
    summary = {
        "files_written": 0,
        "rows_written":  0,
        "empty":         0,
        "schema_errors": 0,
        "row_issues":    0,
        "errors":        0,
    }

    for f in OUTPUT_DIR.glob("*.csv"):
        f.unlink()
        
    try:
        moneyline_files = sorted(glob.glob(str(INPUT_DIR / "*_mlb_moneyline.csv")))
        run_line_files  = sorted(glob.glob(str(INPUT_DIR / "*_mlb_run_line.csv")))
        total_files     = sorted(glob.glob(str(INPUT_DIR / "*_mlb_total.csv")))

        log(f"Moneyline files: {len(moneyline_files)}")
        log(f"Run line files: {len(run_line_files)}")
        log(f"Total files: {len(total_files)}")

        for f in moneyline_files:
            process_moneyline(f, summary)

        for f in run_line_files:
            process_run_line(f, summary)

        for f in total_files:
            process_total(f, summary)

        log("--- SUMMARY ---")
        log(f"Files written: {summary['files_written']}")
        log(f"Rows written: {summary['rows_written']}")
        log(f"Empty files: {summary['empty']}")
        log(f"Schema errors: {summary['schema_errors']}")
        log(f"Row issues: {summary['row_issues']}")
        log(f"Errors: {summary['errors']}")
        log("STATUS: SUCCESS")

    except Exception as e:
        log(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
        log("STATUS: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
