#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/combine_trim_basketball.py

import pandas as pd
from pathlib import Path

###############################################################
######################## PATH CONFIG ##########################
###############################################################

SELECT_DIR = Path("docs/win/basketball/04_select")
OUTPUT_DIR = SELECT_DIR / "daily_slate"
TOTALS_DIR = OUTPUT_DIR / "totals"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_DIR.mkdir(parents=True, exist_ok=True)

###############################################################
######################## LEAGUE SPLIT #########################
###############################################################

def split_leagues(df):

    market_series = df["market"].astype(str).str.upper().str.strip() if "market" in df.columns else pd.Series("", index=df.index)
    league_series = df["league"].astype(str).str.upper().str.strip() if "league" in df.columns else pd.Series("", index=df.index)

    nba_mask = market_series.eq("NBA") | league_series.eq("NBA")
    ncaab_mask = market_series.eq("NCAAB") | league_series.eq("NCAAB")

    nba_df = df[nba_mask].copy()
    ncaab_df = df[ncaab_mask].copy()

    return nba_df, ncaab_df


###############################################################
######################## TOTAL HISTORY ########################
###############################################################

def build_totals():

    nba_files = sorted(OUTPUT_DIR.glob("*_nba.csv"))
    ncaab_files = sorted(OUTPUT_DIR.glob("*_ncaab.csv"))

    nba_final_path = TOTALS_DIR / "NBA_final.csv"
    ncaab_final_path = TOTALS_DIR / "NCAAB_final.csv"

    if nba_files:
        nba_dfs = [pd.read_csv(f) for f in nba_files if f.is_file()]
        if nba_dfs:
            nba_final = pd.concat(nba_dfs, ignore_index=True)
            nba_final.to_csv(nba_final_path, index=False)
    elif nba_final_path.exists():
        nba_final_path.unlink()

    if ncaab_files:
        ncaab_dfs = [pd.read_csv(f) for f in ncaab_files if f.is_file()]
        if ncaab_dfs:
            ncaab_final = pd.concat(ncaab_dfs, ignore_index=True)
            ncaab_final.to_csv(ncaab_final_path, index=False)
    elif ncaab_final_path.exists():
        ncaab_final_path.unlink()

    print("Totals history files created.")


###############################################################
######################## MAIN PIPELINE ########################
###############################################################

def clear_daily_slate_outputs():

    for f in OUTPUT_DIR.glob("*.csv"):
        f.unlink(missing_ok=True)

    for f in TOTALS_DIR.glob("*.csv"):
        f.unlink(missing_ok=True)


def main():

    clear_daily_slate_outputs()

    files = [
        f for f in SELECT_DIR.glob("*.csv")
        if f.is_file() and f.name not in ["nba_selected.csv", "ncaab_selected.csv"]
    ]

    if not files:
        print("No select files found.")
        return

    dfs = []

    for f in files:
        try:
            df = pd.read_csv(f)
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not dfs:
        print("No data to process.")
        return

    df = pd.concat(dfs, ignore_index=True)

    nba_df, ncaab_df = split_leagues(df)

    nba_master = OUTPUT_DIR / "nba_selected.csv"
    ncaab_master = OUTPUT_DIR / "ncaab_selected.csv"

    if not nba_df.empty:
        nba_df.to_csv(nba_master, index=False)
        print(f"NBA master file created: {nba_master}")
    elif nba_master.exists():
        nba_master.unlink(missing_ok=True)

    if not ncaab_df.empty:
        ncaab_df.to_csv(ncaab_master, index=False)
        print(f"NCAAB master file created: {ncaab_master}")
    elif ncaab_master.exists():
        ncaab_master.unlink(missing_ok=True)

    if not nba_df.empty:
        for date, g in nba_df.groupby("game_date", dropna=False):
            path = OUTPUT_DIR / f"{date}_nba.csv"
            g.to_csv(path, index=False)

    if not ncaab_df.empty:
        for date, g in ncaab_df.groupby("game_date", dropna=False):
            path = OUTPUT_DIR / f"{date}_ncaab.csv"
            g.to_csv(path, index=False)

    print("Daily slate files created.")

    build_totals()


if __name__ == "__main__":
    main()
