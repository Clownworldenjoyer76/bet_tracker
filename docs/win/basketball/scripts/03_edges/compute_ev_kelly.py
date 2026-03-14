#!/usr/bin/env python3
# docs/win/basketball/scripts/03_edges/compute_ev_kelly.py

import pandas as pd
from pathlib import Path
import numpy as np
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/03_edges/ev_kelly")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def to_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def implied_prob(decimal_odds):
    return 1 / decimal_odds


def compute_ev(model_decimal, book_decimal):

    p = implied_prob(model_decimal)
    b = book_decimal - 1

    return (p * b) - (1 - p)


def compute_kelly(model_decimal, book_decimal):

    p = implied_prob(model_decimal)
    b = book_decimal - 1
    q = 1 - p

    k = ((b * p) - q) / b

    return np.maximum(k, 0)


# =========================
# MONEYLINE
# =========================

def process_moneyline(df):

    numeric_cols = [
        "home_ml_edge_decimal",
        "away_ml_edge_decimal",
        "home_juice_decimal_moneyline",
        "away_juice_decimal_moneyline",
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline"
    ]

    df = to_numeric(df, numeric_cols)

    df["home_ml_edge_pct"] = df["home_ml_edge_decimal"] * 100
    df["away_ml_edge_pct"] = df["away_ml_edge_decimal"] * 100

    df["home_ml_ev"] = compute_ev(
        df["home_juice_decimal_moneyline"],
        df["home_dk_decimal_moneyline"]
    )

    df["away_ml_ev"] = compute_ev(
        df["away_juice_decimal_moneyline"],
        df["away_dk_decimal_moneyline"]
    )

    df["home_ml_kelly"] = compute_kelly(
        df["home_juice_decimal_moneyline"],
        df["home_dk_decimal_moneyline"]
    )

    df["away_ml_kelly"] = compute_kelly(
        df["away_juice_decimal_moneyline"],
        df["away_dk_decimal_moneyline"]
    )

    return df


# =========================
# SPREAD
# =========================

def process_spread(df):

    numeric_cols = [
        "home_spread_edge_decimal",
        "away_spread_edge_decimal",
        "home_spread_juice_decimal",
        "away_spread_juice_decimal",
        "home_dk_spread_decimal",
        "away_dk_spread_decimal"
    ]

    df = to_numeric(df, numeric_cols)

    df["home_spread_edge_pct"] = df["home_spread_edge_decimal"] * 100
    df["away_spread_edge_pct"] = df["away_spread_edge_decimal"] * 100

    df["home_spread_ev"] = compute_ev(
        df["home_spread_juice_decimal"],
        df["home_dk_spread_decimal"]
    )

    df["away_spread_ev"] = compute_ev(
        df["away_spread_juice_decimal"],
        df["away_dk_spread_decimal"]
    )

    df["home_spread_kelly"] = compute_kelly(
        df["home_spread_juice_decimal"],
        df["home_dk_spread_decimal"]
    )

    df["away_spread_kelly"] = compute_kelly(
        df["away_spread_juice_decimal"],
        df["away_dk_spread_decimal"]
    )

    return df


# =========================
# TOTALS
# =========================

def process_totals(df):

    numeric_cols = [
        "over_edge_decimal",
        "under_edge_decimal",
        "total_over_juice_decimal",
        "total_under_juice_decimal",
        "dk_total_over_decimal",
        "dk_total_under_decimal"
    ]

    df = to_numeric(df, numeric_cols)

    df["over_edge_pct"] = df["over_edge_decimal"] * 100
    df["under_edge_pct"] = df["under_edge_decimal"] * 100

    df["over_ev"] = compute_ev(
        df["total_over_juice_decimal"],
        df["dk_total_over_decimal"]
    )

    df["under_ev"] = compute_ev(
        df["total_under_juice_decimal"],
        df["dk_total_under_decimal"]
    )

    df["over_kelly"] = compute_kelly(
        df["total_over_juice_decimal"],
        df["dk_total_over_decimal"]
    )

    df["under_kelly"] = compute_kelly(
        df["total_under_juice_decimal"],
        df["dk_total_under_decimal"]
    )

    return df


# =========================
# MAIN
# =========================

def main():

    files = list(INPUT_DIR.glob("*.csv"))

    for f in files:

        try:

            df = pd.read_csv(f)

            name = f.name.lower()

            if "moneyline" in name:
                df = process_moneyline(df)

            elif "spread" in name:
                df = process_spread(df)

            elif "total" in name:
                df = process_totals(df)

            out = OUTPUT_DIR / f.name
            df.to_csv(out, index=False)

            print("Processed:", f.name)

        except Exception:
            print("FAILED:", f.name)
            print(traceback.format_exc())


if __name__ == "__main__":
    main()
