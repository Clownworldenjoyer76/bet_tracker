#!/usr/bin/env python3
# scripts/daily_picks.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

###############################################################
# PATH CONFIG
###############################################################

BASEBALL_DIR = Path("docs/win/baseball/04_select")
HOCKEY_DIR = Path("docs/win/hockey/04_select")
NBA_FILE = Path("docs/win/basketball/04_select/daily_slate/nba_selected.csv")
NCAAB_FILE = Path("docs/win/basketball/04_select/daily_slate/ncaab_selected.csv")

OUTPUT_DIR = Path("docs/win/final_scores/daily_picks")
ERROR_DIR = Path("docs/win/final_scores/errors")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "daily_picks.txt"

###############################################################
# HELPERS
###############################################################

def log_error(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def load_csv_safe(path):
    try:
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()
    except Exception:
        log_error(f"Failed reading {path}\n{traceback.format_exc()}")
        return pd.DataFrame()


def normalize_columns(df, league_value):
    if df.empty:
        return df

    cols_needed = [
        "game_id",
        "game_date",
        "game_time",
        "home_team",
        "away_team",
        "bet_side",
        "market_type",
        "line"
    ]

    missing = [c for c in cols_needed if c not in df.columns]
    if missing:
        log_error(f"Missing columns {missing}")
        return pd.DataFrame()

    out = df[cols_needed].copy()
    out.insert(0, "league", league_value)

    return out


def collect_all_inputs():
    dfs = []

    # Baseball files (loop all dates)
    for f in BASEBALL_DIR.glob("*_MLB.csv"):
        df = load_csv_safe(f)
        if not df.empty:
            dfs.append(normalize_columns(df, "NBA"))  # per instruction

    # Hockey files (loop all dates)
    for f in HOCKEY_DIR.glob("*_NHL.csv"):
        df = load_csv_safe(f)
        if not df.empty:
            dfs.append(normalize_columns(df, "NHL"))

    # NBA (single file, assumed current day)
    df_nba = load_csv_safe(NBA_FILE)
    if not df_nba.empty:
        dfs.append(normalize_columns(df_nba, "NBA"))

    # NCAAB (single file, assumed current day)
    df_ncaab = load_csv_safe(NCAAB_FILE)
    if not df_ncaab.empty:
        dfs.append(normalize_columns(df_ncaab, "NCAAB"))

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


###############################################################
# MAIN
###############################################################

def main():
    try:
        df = collect_all_inputs()

        if df.empty:
            log_error("No data found across all inputs")
            return

        # Ensure date format consistency
        df["game_date"] = df["game_date"].astype(str).str.replace("-", "_")

        # Group by date → 1 file per day
        for game_date, group in df.groupby("game_date"):
            try:
                output_file = OUTPUT_DIR / f"{game_date}_daily_picks.csv"
                group.to_csv(output_file, index=False)
            except Exception:
                log_error(f"Failed writing file for {game_date}\n{traceback.format_exc()}")

    except Exception:
        log_error(traceback.format_exc())


if __name__ == "__main__":
    main()
