#!/usr/bin/env python3
# docs/win/hockey/scripts/03_edges/compute_ev_kelly.py

import pandas as pd
from pathlib import Path
import numpy as np
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/hockey/03_edges")
OUTPUT_DIR = Path("docs/win/hockey/03_edges/ev_kelly")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        "away_edge_decimal_moneyline"
    ]

    df = to_numeric(df, numeric_cols)

    df["home_ml_edge_pct"] = df["home_edge_decimal_moneyline"] * 100
    df["away_ml_edge_pct"] = df["away_edge_decimal_moneyline"] * 100

    df["home_ml_ev"] = compute_ev(
        df["home_prob"],
        df["home_dk_decimal_moneyline"]
    )

    df["away_ml_ev"] = compute_ev(
        df["away_prob"],
        df["away_dk_decimal_moneyline"]
    )

    df["home_ml_kelly"] = compute_kelly(
        df["home_prob"],
        df["home_dk_decimal_moneyline"]
    )

    df["away_ml_kelly"] = compute_kelly(
        df["away_prob"],
        df["away_dk_decimal_moneyline"]
    )

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
        "away_edge_decimal_puck_line"
    ]

    df = to_numeric(df, numeric_cols)

    df["home_puck_line_edge_pct"] = df["home_edge_decimal_puck_line"] * 100
    df["away_puck_line_edge_pct"] = df["away_edge_decimal_puck_line"] * 100

    df["home_puck_line_ev"] = compute_ev(
        df["home_prob_puck_line"],
        df["home_dk_puck_line_decimal"]
    )

    df["away_puck_line_ev"] = compute_ev(
        df["away_prob_puck_line"],
        df["away_dk_puck_line_decimal"]
    )

    df["home_puck_line_kelly"] = compute_kelly(
        df["home_prob_puck_line"],
        df["home_dk_puck_line_decimal"]
    )

    df["away_puck_line_kelly"] = compute_kelly(
        df["away_prob_puck_line"],
        df["away_dk_puck_line_decimal"]
    )

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
        "under_edge_decimal_total"
    ]

    df = to_numeric(df, numeric_cols)

    df["over_prob"] = 1 / df["fair_total_over_decimal"]
    df["under_prob"] = 1 / df["fair_total_under_decimal"]

    df["over_edge_pct"] = df["over_edge_decimal_total"] * 100
    df["under_edge_pct"] = df["under_edge_decimal_total"] * 100

    df["over_ev"] = compute_ev(
        df["over_prob"],
        df["dk_total_over_decimal"]
    )

    df["under_ev"] = compute_ev(
        df["under_prob"],
        df["dk_total_under_decimal"]
    )

    df["over_kelly"] = compute_kelly(
        df["over_prob"],
        df["dk_total_over_decimal"]
    )

    df["under_kelly"] = compute_kelly(
        df["under_prob"],
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

            elif "puck_line" in name:
                df = process_puck_line(df)

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