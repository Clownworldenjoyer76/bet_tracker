#!/usr/bin/env python3

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


def log(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{datetime.now(UTC).isoformat()} | {msg}\n")


def safe_edge(dk, p):
    dk = pd.to_numeric(dk, errors="coerce")
    p = pd.to_numeric(p, errors="coerce")

    out = pd.Series(np.nan, index=dk.index)
    valid = (dk > 1) & (p > 0) & (p < 1)

    out[valid] = p[valid] * dk[valid] - 1
    return out


# =========================
# RUN LINE (FIXED)
# =========================

def compute_run_line(df):

    df["home_edge_decimal_run_line"] = safe_edge(
        df["home_dk_run_line_decimal"],
        df["home_normalized_prob_run_line"],
    )
    df["away_edge_decimal_run_line"] = safe_edge(
        df["away_dk_run_line_decimal"],
        df["away_normalized_prob_run_line"],
    )

    return df


# =========================
# MONEYLINE
# =========================

def compute_moneyline(df):

    df["home_edge_decimal_moneyline"] = safe_edge(
        df["home_dk_decimal_moneyline"],
        df["home_normalized_prob_moneyline"],
    )
    df["away_edge_decimal_moneyline"] = safe_edge(
        df["away_dk_decimal_moneyline"],
        df["away_normalized_prob_moneyline"],
    )

    return df


# =========================
# TOTAL
# =========================

def compute_total(df):

    df["over_prob"] = 1 / pd.to_numeric(df["fair_total_over_decimal"], errors="coerce")
    df["under_prob"] = 1 / pd.to_numeric(df["fair_total_under_decimal"], errors="coerce")

    df["over_edge_decimal_total"] = safe_edge(
        df["dk_total_over_decimal"],
        df["over_normalized_prob_total"],
    )
    df["under_edge_decimal_total"] = safe_edge(
        df["dk_total_under_decimal"],
        df["under_normalized_prob_total"],
    )

    return df


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w") as f:
        f.write("START\n")

    files = sorted(INPUT_DIR.glob("*.csv"))

    for f in files:
        try:
            df = pd.read_csv(f)
            name = f.name.lower()

            if "run_line" in name:
                df = compute_run_line(df)
            elif "moneyline" in name:
                df = compute_moneyline(df)
            elif "total" in name:
                df = compute_total(df)
            else:
                continue

            df.to_csv(OUTPUT_DIR / f.name, index=False)

        except Exception as e:
            log(str(e))
            log(traceback.format_exc())


if __name__ == "__main__":
    main()