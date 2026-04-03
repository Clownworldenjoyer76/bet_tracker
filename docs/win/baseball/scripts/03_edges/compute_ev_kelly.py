#!/usr/bin/env python3
# docs/win/baseball/scripts/03_edges/compute_ev_kelly.py

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, UTC

INPUT_DIR = Path("docs/win/baseball/02_juice")   # 🔥 FIXED (was wrong)
OUTPUT_DIR = Path("docs/win/baseball/03_edges/ev_kelly")
ERROR_DIR = Path("docs/win/baseball/errors/03_edges")
ERROR_LOG = ERROR_DIR / "compute_ev_kelly.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(msg + "\n")


def compute_ev(p, dec):
    return (p * dec) - 1


def compute_kelly(p, dec):
    b = dec - 1
    q = 1 - p
    k = ((b * p) - q) / b
    return np.maximum(k, 0)


# =========================
# MONEYLINE (unchanged)
# =========================

def ml(df):
    df["home_ml_ev"] = compute_ev(df["home_prob"], df["home_dk_decimal_moneyline"])
    df["away_ml_ev"] = compute_ev(df["away_prob"], df["away_dk_decimal_moneyline"])

    df["home_ml_kelly"] = compute_kelly(df["home_prob"], df["home_dk_decimal_moneyline"])
    df["away_ml_kelly"] = compute_kelly(df["away_prob"], df["away_dk_decimal_moneyline"])

    return df


# =========================
# RUN LINE (🔥 FIXED)
# =========================

def rl(df):

    # 🔥 USE JUICED PROBABILITIES (NOT FAIR)
    df["home_rl_ev"] = compute_ev(df["home_juiced_prob_run_line"], df["home_dk_run_line_decimal"])
    df["away_rl_ev"] = compute_ev(df["away_juiced_prob_run_line"], df["away_dk_run_line_decimal"])

    df["home_rl_kelly"] = compute_kelly(df["home_juiced_prob_run_line"], df["home_dk_run_line_decimal"])
    df["away_rl_kelly"] = compute_kelly(df["away_juiced_prob_run_line"], df["away_dk_run_line_decimal"])

    return df


# =========================
# TOTAL (unchanged)
# =========================

def tot(df):

    df["over_prob"] = 1 / df["fair_total_over_decimal"]
    df["under_prob"] = 1 / df["fair_total_under_decimal"]

    df["over_ev"] = compute_ev(df["over_prob"], df["dk_total_over_decimal"])
    df["under_ev"] = compute_ev(df["under_prob"], df["dk_total_under_decimal"])

    df["over_kelly"] = compute_kelly(df["over_prob"], df["dk_total_over_decimal"])
    df["under_kelly"] = compute_kelly(df["under_prob"], df["dk_total_under_decimal"])

    return df


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w") as f:
        f.write("=== EV KELLY START ===\n")

    files = sorted(INPUT_DIR.glob("*.csv"))

    for f in files:
        try:
            df = pd.read_csv(f)
            name = f.name.lower()

            if "moneyline" in name:
                df = ml(df)
            elif "run_line" in name:
                df = rl(df)
            elif "total" in name:
                df = tot(df)
            else:
                continue

            out = OUTPUT_DIR / f.name
            df.to_csv(out, index=False)

            log(f"WROTE {out}")

        except Exception as e:
            log(f"FAILED {f}: {e}")


if __name__ == "__main__":
    main()
