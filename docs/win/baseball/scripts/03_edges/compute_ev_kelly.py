#!/usr/bin/env python3
# docs/win/baseball/scripts/03_edges/compute_ev_kelly.py

import traceback
from datetime import datetime, UTC
from pathlib import Path

import numpy as np
import pandas as pd

INPUT_DIR  = Path("docs/win/baseball/03_edges")
OUTPUT_DIR = Path("docs/win/baseball/03_edges/ev_kelly")
ERROR_DIR  = Path("docs/win/baseball/errors/03_edges")
LOG_FILE   = ERROR_DIR / "compute_ev_kelly.txt"

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
        f"  neg_kelly_clipped: {summary['neg_kelly_clipped']}",
        f"  errors           : {summary['errors']}",
        "",
        f"  {'file':<48} {'market':<12} {'rows':>5} {'neg_kelly':>10} {'status':>10}",
    ]
    for pf in per_file:
        lines.append(
            f"  {pf['name']:<48} {pf['market']:<12} {pf['rows']:>5} "
            f"{pf['neg_kelly']:>10} {pf['status']:>10}"
        )
    status = "SUCCESS" if summary["errors"] == 0 else "COMPLETED WITH ERRORS"
    lines += ["", f"STATUS: {status}", "=" * 60]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# =========================
# HELPERS
# =========================

def compute_ev(p, dec):
    p   = pd.to_numeric(p,   errors="coerce")
    dec = pd.to_numeric(dec, errors="coerce")
    return (p * dec) - 1


def compute_kelly(p, dec, file_name=""):
    p   = pd.to_numeric(p,   errors="coerce")
    dec = pd.to_numeric(dec, errors="coerce")
    b   = dec - 1
    q   = 1 - p
    k   = ((b * p) - q) / b

    neg = k[k.notna() & (k < 0)]
    if not neg.empty:
        _log(f"{file_name} | {len(neg)} negative Kelly values clipped to 0 "
             f"(min={neg.min():.4f})", "WARN")

    return np.maximum(k, 0), len(neg)


# =========================
# MARKET PROCESSORS
# =========================

def process_moneyline(df, file_name):
    df["home_ml_ev"] = compute_ev(df["home_prob"], df["home_dk_decimal_moneyline"])
    df["away_ml_ev"] = compute_ev(df["away_prob"], df["away_dk_decimal_moneyline"])

    home_kelly, h_neg = compute_kelly(df["home_prob"], df["home_dk_decimal_moneyline"], file_name)
    away_kelly, a_neg = compute_kelly(df["away_prob"], df["away_dk_decimal_moneyline"], file_name)

    df["home_ml_kelly"] = home_kelly
    df["away_ml_kelly"] = away_kelly

    return df, h_neg + a_neg


def process_run_line(df, file_name):
    df["home_rl_ev"] = compute_ev(df["home_normalized_prob_run_line"], df["home_dk_run_line_decimal"])
    df["away_rl_ev"] = compute_ev(df["away_normalized_prob_run_line"], df["away_dk_run_line_decimal"])

    home_kelly, h_neg = compute_kelly(df["home_normalized_prob_run_line"], df["home_dk_run_line_decimal"], file_name)
    away_kelly, a_neg = compute_kelly(df["away_normalized_prob_run_line"], df["away_dk_run_line_decimal"], file_name)

    df["home_rl_kelly"] = home_kelly
    df["away_rl_kelly"] = away_kelly

    return df, h_neg + a_neg


def process_total(df, file_name):
    df["over_prob"]  = 1 / pd.to_numeric(df["fair_total_over_decimal"],  errors="coerce")
    df["under_prob"] = 1 / pd.to_numeric(df["fair_total_under_decimal"], errors="coerce")

    df["over_ev"]  = compute_ev(df["over_prob"],  df["dk_total_over_decimal"])
    df["under_ev"] = compute_ev(df["under_prob"], df["dk_total_under_decimal"])

    over_kelly,  o_neg = compute_kelly(df["over_prob"],  df["dk_total_over_decimal"],  file_name)
    under_kelly, u_neg = compute_kelly(df["under_prob"], df["dk_total_under_decimal"], file_name)

    df["over_kelly"]  = over_kelly
    df["under_kelly"] = under_kelly

    return df, o_neg + u_neg


# =========================
# MAIN
# =========================

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== compute_ev_kelly RUN {_now()} ===\n")

    summary = {
        "files_processed": 0, "rows_processed": 0,
        "moneyline_files": 0, "run_line_files": 0, "total_files": 0,
        "skipped": 0, "neg_kelly_clipped": 0, "errors": 0,
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
                  "neg_kelly": 0, "status": "ok"}

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
                df, neg_kelly = process_moneyline(df, f.name)
                summary["moneyline_files"] += 1
            elif market == "run_line":
                df, neg_kelly = process_run_line(df, f.name)
                summary["run_line_files"] += 1
            else:
                df, neg_kelly = process_total(df, f.name)
                summary["total_files"] += 1

            pf["neg_kelly"]              = neg_kelly
            summary["neg_kelly_clipped"] += neg_kelly

            df.to_csv(OUTPUT_DIR / f.name, index=False)
            summary["files_processed"] += 1
            _log(f"WROTE: {OUTPUT_DIR / f.name} ({len(df)} rows, {neg_kelly} kelly clipped)")

        except Exception as e:
            _log(f"{f.name} FAILED: {e}\n{traceback.format_exc()}", "ERROR")
            pf["status"] = "error"
            summary["errors"] += 1

        per_file.append(pf)

    _write_summary(summary, per_file)
    print("compute_ev_kelly complete.")


if __name__ == "__main__":
    main()
