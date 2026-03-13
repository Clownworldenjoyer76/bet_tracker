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

MARKET_TALLY_INPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final_sorted.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/ncaab_final_sorted.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/nhl_final_sorted.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/soccer_final_sorted.csv"),
}

MARKET_TALLY_OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/market_tally_NBA.csv"),
    "NCAAB": Path("docs/win/final_scores/results/market_tally_NCAAB.csv"),
    "NHL": Path("docs/win/final_scores/results/market_tally_NHL.csv"),
    "SOCCER": Path("docs/win/final_scores/results/market_tally_SOCCER.csv"),
}

ERROR_LOG = Path("docs/win/final_scores/errors/results_sorted_errors.txt")


# =========================
# HELPERS
# =========================

def log(msg: str) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def safe_read(path: Path) -> pd.DataFrame:
    try:
        if not path.exists():
            log(f"Missing input: {path}")
            return pd.DataFrame()
        df = pd.read_csv(path)
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        log(f"ERROR reading {path}: {e}")
        return pd.DataFrame()


def normalize_result(df: pd.DataFrame) -> pd.DataFrame:
    if "bet_result" in df.columns:
        df["bet_result"] = df["bet_result"].astype(str).str.strip().str.title()
    return df


def summarize_wl(df: pd.DataFrame):

    wins = int((df["bet_result"] == "Win").sum())
    losses = int((df["bet_result"] == "Loss").sum())
    pushes = int((df["bet_result"] == "Push").sum())

    total = wins + losses + pushes
    denom = wins + losses
    win_pct = float(wins / denom) if denom > 0 else 0

    return wins, losses, pushes, total, win_pct


# =========================
# SUMMARY BUILDERS
# =========================

def generic_summary(df: pd.DataFrame, market_name: str):

    rows = []

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
            "Win_Pct": round(win_pct, 4)
        })

    return pd.DataFrame(rows)


# =========================
# SOCCER SUMMARY
# =========================

def soccer_summary(df: pd.DataFrame):

    rows = []

    for m in ["result", "total"]:

        sub = df[df["market_type"] == m]

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        rows.append({
            "market": "SOCCER",
            "market_type": m,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4)
        })

    return pd.DataFrame(rows)


# =========================
# BUILD SORTED OUTPUT
# =========================

def build_sorted_output(df: pd.DataFrame, market_name: str):

    df = normalize_result(df)

    if market_name == "SOCCER":
        summary = soccer_summary(df)
    else:
        summary = generic_summary(df, market_name)

    return summary


# =========================
# MARKET TALLY
# =========================

def create_market_tally_file(market_name: str, in_path: Path, out_path: Path):

    df = safe_read(in_path)

    if df.empty:
        log(f"{market_name}: Input empty {in_path}")
        return

    df = normalize_result(df)

    rows = []

    if market_name in ["NBA", "NCAAB"]:
        markets = ["moneyline", "spread", "total"]
    elif market_name == "NHL":
        markets = ["moneyline", "puck_line", "total"]
    else:
        markets = ["result", "total"]

    for m in markets:

        sub = df[df["market_type"] == m]

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        rows.append({
            "market": market_name,
            "market_type": m,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4)
        })

    out = pd.DataFrame(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    log(f"{market_name}: wrote tally {out_path}")


def create_all_market_tally_files():

    for m, path in MARKET_TALLY_INPUTS.items():

        create_market_tally_file(
            m,
            path,
            MARKET_TALLY_OUTPUTS[m]
        )


# =========================
# MAIN
# =========================

def main():

    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== results_sorted.py log ===\n")

    for market_name, in_path in INPUTS.items():

        df = safe_read(in_path)

        if df.empty:

            log(f"{market_name}: input empty")

            continue

        out_df = build_sorted_output(df, market_name)

        out_path = OUTPUTS[market_name]

        out_path.parent.mkdir(parents=True, exist_ok=True)

        out_df.to_csv(out_path, index=False)

        log(f"{market_name}: wrote sorted file {out_path}")

    create_all_market_tally_files()

    print("results_sorted.py complete.")


if __name__ == "__main__":
    main()
