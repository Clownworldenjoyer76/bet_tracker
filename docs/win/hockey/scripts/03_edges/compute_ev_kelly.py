#!/usr/bin/env python3
# docs/win/hockey/scripts/03_edges/compute_ev_kelly.py

import pandas as pd
from pathlib import Path
import numpy as np
import traceback
from datetime import datetime, UTC

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/hockey/03_edges")
OUTPUT_DIR = Path("docs/win/hockey/03_edges/ev_kelly")

ERROR_DIR = Path("docs/win/hockey/errors/03_edges")
ERROR_LOG = ERROR_DIR / "compute_ev_kelly.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# LOGGING
# =========================

def log(msg: str) -> None:
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")


def _now() -> str:
    return datetime.now(UTC).isoformat()


# =========================
# HELPERS
# =========================

def to_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def compute_ev(model_prob, book_decimal):
    model_prob = pd.to_numeric(model_prob, errors="coerce")
    book_decimal = pd.to_numeric(book_decimal, errors="coerce")
    return (model_prob * book_decimal) - 1


def compute_kelly(model_prob, book_decimal):
    model_prob = pd.to_numeric(model_prob, errors="coerce")
    book_decimal = pd.to_numeric(book_decimal, errors="coerce")

    b = book_decimal - 1
    q = 1 - model_prob

    k = ((b * model_prob) - q) / b

    negative_kelly = k[k.notna() & (k < 0)]
    if not negative_kelly.empty:
        log(f"[WARN] Negative Kelly clipped to 0 for {len(negative_kelly)} row(s): min={negative_kelly.min():.4f}")

    return np.maximum(k, 0)


# =========================
# MONEYLINE
# =========================

def process_moneyline(df):

    numeric_cols = [
        "home_prob",
        "away_prob",
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline",
        "home_edge_decimal_moneyline",
        "away_edge_decimal_moneyline",
    ]

    df = to_numeric(df, numeric_cols)

    df["home_ml_edge_pct"] = df["home_edge_decimal_moneyline"] * 100
    df["away_ml_edge_pct"] = df["away_edge_decimal_moneyline"] * 100

    df["home_ml_ev"] = compute_ev(df["home_prob"], df["home_dk_decimal_moneyline"])
    df["away_ml_ev"] = compute_ev(df["away_prob"], df["away_dk_decimal_moneyline"])

    df["home_ml_kelly"] = compute_kelly(df["home_prob"], df["home_dk_decimal_moneyline"])
    df["away_ml_kelly"] = compute_kelly(df["away_prob"], df["away_dk_decimal_moneyline"])

    return df


# =========================
# PUCK LINE
# =========================

def process_puck_line(df):

    numeric_cols = [
        "home_prob_puck_line",
        "away_prob_puck_line",
        "home_dk_puck_line_decimal",
        "away_dk_puck_line_decimal",
        "home_edge_decimal_puck_line",
        "away_edge_decimal_puck_line",
    ]

    df = to_numeric(df, numeric_cols)

    df["home_puck_line_edge_pct"] = df["home_edge_decimal_puck_line"] * 100
    df["away_puck_line_edge_pct"] = df["away_edge_decimal_puck_line"] * 100

    df["home_puck_line_ev"] = compute_ev(df["home_prob_puck_line"], df["home_dk_puck_line_decimal"])
    df["away_puck_line_ev"] = compute_ev(df["away_prob_puck_line"], df["away_dk_puck_line_decimal"])

    df["home_puck_line_kelly"] = compute_kelly(df["home_prob_puck_line"], df["home_dk_puck_line_decimal"])
    df["away_puck_line_kelly"] = compute_kelly(df["away_prob_puck_line"], df["away_dk_puck_line_decimal"])

    return df


# =========================
# TOTALS
# =========================

def process_totals(df):

    numeric_cols = [
        "fair_total_over_decimal",
        "fair_total_under_decimal",
        "dk_total_over_decimal",
        "dk_total_under_decimal",
        "over_edge_decimal_total",
        "under_edge_decimal_total",
    ]

    df = to_numeric(df, numeric_cols)

    over_dec = pd.to_numeric(df["fair_total_over_decimal"], errors="coerce")
    under_dec = pd.to_numeric(df["fair_total_under_decimal"], errors="coerce")
    df["over_prob"] = over_dec.where(over_dec > 0).apply(lambda x: 1 / x if pd.notna(x) else pd.NA)
    df["under_prob"] = under_dec.where(under_dec > 0).apply(lambda x: 1 / x if pd.notna(x) else pd.NA)

    df["over_edge_pct"] = df["over_edge_decimal_total"] * 100
    df["under_edge_pct"] = df["under_edge_decimal_total"] * 100

    df["over_ev"] = compute_ev(df["over_prob"], df["dk_total_over_decimal"])
    df["under_ev"] = compute_ev(df["under_prob"], df["dk_total_under_decimal"])

    df["over_kelly"] = compute_kelly(df["over_prob"], df["dk_total_over_decimal"])
    df["under_kelly"] = compute_kelly(df["under_prob"], df["dk_total_under_decimal"])

    return df


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(f"=== COMPUTE EV KELLY START {_now()} ===\n")

    files = sorted(INPUT_DIR.glob("*.csv"))
    log(f"[INFO] Files found: {len(files)}")

    processed = 0
    failed = 0

    for f in files:

        log(f"\n=== FILE START {_now()} ===")
        log(f"[INFO] {f}")

        try:
            df = pd.read_csv(f)
            name = f.name.lower()

            if "moneyline" in name:
                df = process_moneyline(df)
            elif "puck_line" in name:
                df = process_puck_line(df)
            elif "total" in name:
                df = process_totals(df)
            else:
                log(f"[WARN] Unrecognised file pattern — skipping")
                continue

            out = OUTPUT_DIR / f.name
            df.to_csv(out, index=False)

            log(f"[INFO] Wrote: {out}")
            log(f"=== FILE END {_now()} ===")
            processed += 1

        except Exception:
            log(f"[ERROR] FAILED: {f.name}")
            log(traceback.format_exc())
            log(f"=== FILE END {_now()} ===")
            failed += 1

    log(f"\n[SUMMARY] processed={processed} failed={failed}")
    log(f"=== COMPLETE {_now()} ===")


if __name__ == "__main__":
    main()