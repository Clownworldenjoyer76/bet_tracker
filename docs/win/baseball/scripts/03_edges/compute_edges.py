#!/usr/bin/env python3
# docs/win/baseball/scripts/03_edges/compute_edges.py

import traceback
from datetime import datetime, UTC
from pathlib import Path

import numpy as np
import pandas as pd

INPUT_DIR  = Path("docs/win/baseball/02_juice")
OUTPUT_DIR = Path("docs/win/baseball/03_edges")
ERROR_DIR  = Path("docs/win/baseball/errors/03_edges")
LOG_FILE   = ERROR_DIR / "compute_edges.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# LOGGING
# =========================

def _now():
    return datetime.now(UTC).isoformat()


def _log(msg: str, level: str = "INFO"):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{_now()} | {level:<5} | {msg.rstrip()}\n")


def _write_summary(summary: dict, per_file: list) -> None:
    lines = [
        "",
        "=" * 60,
        f"SUMMARY  {_now()}",
        "=" * 60,
        f"  files_processed  : {summary['files_processed']}",
        f"  rows_processed   : {summary['rows_processed']}",
        f"  moneyline_files  : {summary['moneyline_files']}",
        f"  run_line_files   : {summary['run_line_files']}",
        f"  total_files      : {summary['total_files']}",
        f"  skipped          : {summary['skipped']}",
        f"  null_edges       : {summary['null_edges']}",
        f"  errors           : {summary['errors']}",
        "",
        f"  {'file':<48} {'market':<12} {'rows':>5} {'null_edges':>10} {'status':>10}",
    ]
    for pf in per_file:
        lines.append(
            f"  {pf['name']:<48} {pf['market']:<12} {pf['rows']:>5} "
            f"{pf['null_edges']:>10} {pf['status']:>10}"
        )
    status = "SUCCESS" if summary["errors"] == 0 else "COMPLETED WITH ERRORS"
    lines += ["", f"STATUS: {status}", "=" * 60]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# =========================
# HELPERS
# =========================

def safe_edge(dk, p):
    dk  = pd.to_numeric(dk, errors="coerce")
    p   = pd.to_numeric(p,  errors="coerce")
    out = pd.Series(np.nan, index=dk.index)
    valid = (dk > 1) & (p > 0) & (p < 1) & np.isfinite(dk) & np.isfinite(p)
    out[valid] = p[valid] * dk[valid] - 1
    return out


def count_null_edges(df, cols):
    return sum(df[c].isna().sum() for c in cols if c in df.columns)


# =========================
# MARKET PROCESSORS
# =========================

def compute_moneyline(df):
    df["home_edge_decimal_moneyline"] = safe_edge(
        df["home_dk_decimal_moneyline"], df["home_normalized_prob_moneyline"]
    )
    df["away_edge_decimal_moneyline"] = safe_edge(
        df["away_dk_decimal_moneyline"], df["away_normalized_prob_moneyline"]
    )
    null_edges = count_null_edges(df, [
        "home_edge_decimal_moneyline", "away_edge_decimal_moneyline"
    ])
    return df, null_edges


def compute_run_line(df):
    df["home_edge_decimal_run_line"] = safe_edge(
        df["home_dk_run_line_decimal"], df["home_normalized_prob_run_line"]
    )
    df["away_edge_decimal_run_line"] = safe_edge(
        df["away_dk_run_line_decimal"], df["away_normalized_prob_run_line"]
    )
    null_edges = count_null_edges(df, [
        "home_edge_decimal_run_line", "away_edge_decimal_run_line"
    ])
    return df, null_edges


def compute_total(df):
    df["over_prob"]  = 1 / pd.to_numeric(df["fair_total_over_decimal"],  errors="coerce")
    df["under_prob"] = 1 / pd.to_numeric(df["fair_total_under_decimal"], errors="coerce")
    df["over_edge_decimal_total"]  = safe_edge(df["dk_total_over_decimal"],  df["over_normalized_prob_total"])
    df["under_edge_decimal_total"] = safe_edge(df["dk_total_under_decimal"], df["under_normalized_prob_total"])
    null_edges = count_null_edges(df, [
        "over_edge_decimal_total", "under_edge_decimal_total"
    ])
    return df, null_edges


# =========================
# MAIN
# =========================

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== compute_edges RUN {_now()} ===\n")

    summary = {
        "files_processed": 0, "rows_processed": 0,
        "moneyline_files": 0, "run_line_files": 0, "total_files": 0,
        "skipped": 0, "null_edges": 0, "errors": 0,
    }
    per_file = []

    _log(f"INPUT_DIR : {INPUT_DIR}")
    _log(f"OUTPUT_DIR: {OUTPUT_DIR}")

    input_files = sorted(INPUT_DIR.glob("*.csv"))
    _log(f"Files found: {len(input_files)}")

    for f in input_files:
        name   = f.name.lower()
        market = None
        pf     = {"name": f.name, "market": "unknown", "rows": 0,
                  "null_edges": 0, "status": "ok"}

        if "moneyline" in name:
            market = "moneyline"
        elif "run_line" in name:
            market = "run_line"
        elif "total" in name:
            market = "total"
        else:
            _log(f"SKIP unrecognized file: {f.name}")
            pf["status"] = "skipped"
            summary["skipped"] += 1
            per_file.append(pf)
            continue

        pf["market"] = market
        _log(f"--- FILE: {f.name}  market={market}")

        for f in OUTPUT_DIR.glob("*.csv"):
        f.unlink()
        
        try:
            df = pd.read_csv(f)

            if df.empty:
                _log(f"{f.name} empty — skipping")
                pf["status"] = "empty"
                summary["skipped"] += 1
                per_file.append(pf)
                continue

            pf["rows"] = len(df)
            summary["rows_processed"] += len(df)

            if market == "moneyline":
                df, null_edges = compute_moneyline(df)
                summary["moneyline_files"] += 1
            elif market == "run_line":
                df, null_edges = compute_run_line(df)
                summary["run_line_files"] += 1
            else:
                df, null_edges = compute_total(df)
                summary["total_files"] += 1

            pf["null_edges"]      = null_edges
            summary["null_edges"] += null_edges

            if null_edges > 0:
                _log(f"{f.name} | {null_edges} null edges", "WARN")

            df.to_csv(OUTPUT_DIR / f.name, index=False)
            summary["files_processed"] += 1
            _log(f"WROTE: {OUTPUT_DIR / f.name} ({len(df)} rows, {null_edges} null edges)")

        except Exception as e:
            _log(f"{f.name} FAILED: {e}\n{traceback.format_exc()}", "ERROR")
            pf["status"] = "error"
            summary["errors"] += 1

        per_file.append(pf)

    _write_summary(summary, per_file)
    print("compute_edges complete.")


if __name__ == "__main__":
    main()
