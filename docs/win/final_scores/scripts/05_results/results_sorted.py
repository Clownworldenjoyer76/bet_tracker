#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/results_sorted.py

import os
from pathlib import Path
from datetime import datetime
import pandas as pd


# =========================
# PATHS
# =========================

INPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/NCAAB_final.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/NHL_final.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/SOCCER_final.csv"),
}

OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final_sorted.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/ncaab_final_sorted.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/nhl_final_sorted.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/soccer_final_sorted.csv"),
}

MARKET_TALLY_INPUTS = OUTPUTS

MARKET_TALLY_OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/market_tally_NBA.csv"),
    "NCAAB": Path("docs/win/final_scores/results/market_tally_NCAAB.csv"),
    "NHL": Path("docs/win/final_scores/results/market_tally_NHL.csv"),
    "SOCCER": Path("docs/win/final_scores/results/market_tally_SOCCER.csv"),
}

DEEP_OUTPUT_DIR = Path("docs/win/final_scores/deep_market_breakdowns")

ERROR_LOG = Path("docs/win/final_scores/errors/results_sorted_errors.txt")


# =========================
# LOGGING
# =========================

def log(msg):

    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(ERROR_LOG, "a", encoding="utf-8") as f:

        f.write(f"[{ts}] {msg}\n")


# =========================
# FILE READ
# =========================

def safe_read(path):

    try:

        if not path.exists():

            log(f"Missing input file: {path}")

            return None

        df = pd.read_csv(path)

        if df.empty:

            log(f"Empty file: {path}")

            return None

        return df

    except Exception as e:

        log(f"Error reading {path}: {e}")

        return None


# =========================
# RESULT NORMALIZATION
# =========================

def normalize_result(df):

    if "bet_result" in df.columns:

        df["bet_result"] = (
            df["bet_result"]
            .astype(str)
            .str.strip()
            .str.title()
        )

    return df


# =========================
# WIN LOSS SUMMARY
# =========================

def summarize_wl(df):

    if df is None:
        return 0,0,0,0,0

    if "bet_result" not in df.columns:
        return 0,0,0,0,0

    wins = int((df["bet_result"] == "Win").sum())
    losses = int((df["bet_result"] == "Loss").sum())
    pushes = int((df["bet_result"] == "Push").sum())

    total = wins + losses + pushes

    denom = wins + losses

    win_pct = wins / denom if denom > 0 else 0

    return wins, losses, pushes, total, win_pct


# =========================
# SUMMARY BUILDERS
# =========================

def generic_summary(df, market_name):

    rows = []

    if "market_type" not in df.columns:
        log(f"{market_name} missing market_type column")
        return pd.DataFrame()

    for m in sorted(df["market_type"].dropna().unique()):

        sub = df[df["market_type"] == m]

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        rows.append({
            "market": market_name,
            "market_type": m,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct,4)
        })

    return pd.DataFrame(rows)


def soccer_summary(df):

    rows = []

    for m in ["result","total"]:

        sub = df[df["market_type"] == m]

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        rows.append({
            "market":"SOCCER",
            "market_type":m,
            "Win":wins,
            "Loss":losses,
            "Push":pushes,
            "Total":total,
            "Win_Pct":round(win_pct,4)
        })

    return pd.DataFrame(rows)


# =========================
# DEEP ANALYTICS
# =========================

def build_deep_summary(df, market_name):

    if df is None:
        return pd.DataFrame()

    group_cols = ["market_type"]

    if "bet_side" in df.columns:
        group_cols.append("bet_side")

    if "home_team" in df.columns:
        group_cols.append("home_team")

    rows = []

    grouped = df.groupby(group_cols)

    for keys, sub in grouped:

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        if not isinstance(keys, tuple):
            keys = (keys,)

        row = {
            "market":market_name,
            "Win":wins,
            "Loss":losses,
            "Push":pushes,
            "Total":total,
            "Win_Pct":round(win_pct,4)
        }

        for i,col in enumerate(group_cols):
            row[col] = keys[i]

        rows.append(row)

    return pd.DataFrame(rows)


def write_deep_summary(df, market_name):

    if df is None:
        return

    DEEP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    deep = build_deep_summary(df, market_name)

    out_path = DEEP_OUTPUT_DIR / f"{market_name}_deep_summary.csv"

    deep.to_csv(out_path,index=False)

    log(f"Wrote deep summary {out_path}")


# =========================
# SORTED OUTPUT
# =========================

def build_sorted_output(df, market_name):

    df = normalize_result(df)

    if market_name == "SOCCER":
        return soccer_summary(df)

    return generic_summary(df,market_name)


# =========================
# MARKET TALLY
# =========================

def create_market_tally_file(market_name, in_path, out_path):

    df = safe_read(in_path)

    if df is None:
        log(f"{market_name} tally skipped, missing input")
        return

    if not {"Win","Loss","Push","Total","Win_Pct"}.issubset(df.columns):
        log(f"{market_name} tally skipped, required columns missing")
        return

    df["market"] = market_name

    out = df[["market","market_type","Win","Loss","Push","Total","Win_Pct"]]

    out_path.parent.mkdir(parents=True,exist_ok=True)

    out.to_csv(out_path,index=False)

    log(f"Wrote market tally {out_path}")


def create_all_market_tally_files():

    for m,path in MARKET_TALLY_INPUTS.items():

        create_market_tally_file(
            m,
            path,
            MARKET_TALLY_OUTPUTS[m]
        )


# =========================
# MAIN
# =========================

def main():

    ERROR_LOG.parent.mkdir(parents=True,exist_ok=True)

    with open(ERROR_LOG,"w",encoding="utf-8") as f:
        f.write("=== results_sorted.py log ===\n")

    for market_name,in_path in INPUTS.items():

        df = safe_read(in_path)

        if df is None:

            log(f"{market_name} skipped (missing input)")

            continue

        out_df = build_sorted_output(df,market_name)

        out_path = OUTPUTS[market_name]

        out_path.parent.mkdir(parents=True,exist_ok=True)

        out_df.to_csv(out_path,index=False)

        log(f"{market_name} sorted output written")

        write_deep_summary(df,market_name)

    create_all_market_tally_files()

    print("results_sorted.py complete.")


if __name__ == "__main__":
    main()
