#!/usr/bin/env python3
# docs/win/baseball/scripts/03_edges/compute_edges.py

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, UTC
import traceback

INPUT_DIR = Path("docs/win/baseball/02_juice")
OUTPUT_DIR = Path("docs/win/baseball/03_edges")
ERROR_DIR = Path("docs/win/baseball/errors/03_edges")
ERROR_LOG = ERROR_DIR / "compute_edges.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(UTC).isoformat()} | {msg}\n")


def validate_columns(df, required, file_path):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{file_path} missing required columns: {missing}")


def safe_edge_decimal(dk, p):
    dk = pd.to_numeric(dk, errors="coerce")
    p = pd.to_numeric(p, errors="coerce")

    out = pd.Series(np.nan, index=dk.index)
    valid = (dk > 1) & (p > 0) & (p < 1)

    out[valid] = p[valid] * dk[valid] - 1
    return out


def safe_edge_pct(dk, p):
    dk = pd.to_numeric(dk, errors="coerce")
    p = pd.to_numeric(p, errors="coerce")

    edge = pd.Series(np.nan, index=dk.index)
    valid = (dk > 1) & (p > 0) & (p < 1)

    market = 1 / dk[valid]
    edge[valid] = p[valid] - market
    return edge


# =========================
# MONEYLINE
# =========================

def compute_moneyline(df, file_path):
    required = [
        "game_id",
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline",
        "home_normalized_prob_moneyline",
        "away_normalized_prob_moneyline",
        "home_prob",
        "away_prob",
    ]
    validate_columns(df, required, file_path)

    df["home_edge_decimal_moneyline"] = safe_edge_decimal(
        df["home_dk_decimal_moneyline"],
        df["home_normalized_prob_moneyline"],
    )
    df["away_edge_decimal_moneyline"] = safe_edge_decimal(
        df["away_dk_decimal_moneyline"],
        df["away_normalized_prob_moneyline"],
    )

    df["home_raw_edge_decimal_moneyline"] = safe_edge_decimal(
        df["home_dk_decimal_moneyline"],
        df["home_prob"],
    )
    df["away_raw_edge_decimal_moneyline"] = safe_edge_decimal(
        df["away_dk_decimal_moneyline"],
        df["away_prob"],
    )

    df["home_edge_pct_moneyline"] = safe_edge_pct(
        df["home_dk_decimal_moneyline"],
        df["home_normalized_prob_moneyline"],
    )
    df["away_edge_pct_moneyline"] = safe_edge_pct(
        df["away_dk_decimal_moneyline"],
        df["away_normalized_prob_moneyline"],
    )

    return df


# =========================
# RUN LINE
# =========================

def compute_run_line(df, file_path):

    required = [
        "game_id",
        "home_dk_run_line_decimal",
        "away_dk_run_line_decimal",
        "home_normalized_prob_run_line",
        "away_normalized_prob_run_line",
        "home_prob_run_line",
        "away_prob_run_line",
    ]
    validate_columns(df, required, file_path)

    df["home_edge_decimal_run_line"] = safe_edge_decimal(
        df["home_dk_run_line_decimal"],
        df["home_normalized_prob_run_line"],
    )
    df["away_edge_decimal_run_line"] = safe_edge_decimal(
        df["away_dk_run_line_decimal"],
        df["away_normalized_prob_run_line"],
    )

    df["home_raw_edge_decimal_run_line"] = safe_edge_decimal(
        df["home_dk_run_line_decimal"],
        df["home_prob_run_line"],
    )
    df["away_raw_edge_decimal_run_line"] = safe_edge_decimal(
        df["away_dk_run_line_decimal"],
        df["away_prob_run_line"],
    )

    return df


# =========================
# TOTAL
# =========================

def compute_total(df, file_path):

    required = [
        "game_id",
        "dk_total_over_decimal",
        "dk_total_under_decimal",
        "over_normalized_prob_total",
        "under_normalized_prob_total",
        "fair_total_over_decimal",
        "fair_total_under_decimal",
    ]
    validate_columns(df, required, file_path)

    df["over_prob"] = 1 / pd.to_numeric(df["fair_total_over_decimal"], errors="coerce")
    df["under_prob"] = 1 / pd.to_numeric(df["fair_total_under_decimal"], errors="coerce")

    df["over_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_over_decimal"],
        df["over_normalized_prob_total"],
    )
    df["under_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_under_decimal"],
        df["under_normalized_prob_total"],
    )

    df["over_raw_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_over_decimal"],
        df["over_prob"],
    )
    df["under_raw_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_under_decimal"],
        df["under_prob"],
    )

    return df


# =========================
# DRIVER
# =========================

def main():

    with open(ERROR_LOG, "w") as f:
        f.write("=== BASEBALL COMPUTE EDGES ===\n")

    files = sorted(INPUT_DIR.glob("*.csv"))

    for f in files:
        try:
            df = pd.read_csv(f)
            name = f.name.lower()

            if "moneyline" in name:
                df = compute_moneyline(df, f)
            elif "run_line" in name:
                df = compute_run_line(df, f)
            elif "total" in name:
                df = compute_total(df, f)
            else:
                continue

            out = OUTPUT_DIR / f.name
            df.to_csv(out, index=False)

            log(f"WROTE {out}")

        except Exception as e:
            log(f"FAILED {f}: {e}")
            log(traceback.format_exc())


if __name__ == "__main__":
    main()