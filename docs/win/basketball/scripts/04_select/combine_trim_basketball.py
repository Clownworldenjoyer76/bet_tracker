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
######################## EDGE CALCULATION #####################
###############################################################

def compute_edge(row):

    market_type = str(row.get("market_type", "")).lower()

    if market_type == "total":

        bet_side = str(row.get("bet_side", "")).lower()

        if bet_side == "over":
            return float(row.get("over_edge_decimal", 0) or 0)

        if bet_side == "under":
            return float(row.get("under_edge_decimal", 0) or 0)

        return 0

    if market_type == "moneyline":

        return max(
            float(row.get("home_ml_edge_decimal", 0) or 0),
            float(row.get("away_ml_edge_decimal", 0) or 0),
        )

    if market_type == "spread":

        return max(
            float(row.get("home_spread_edge_decimal", 0) or 0),
            float(row.get("away_spread_edge_decimal", 0) or 0),
        )

    return 0


###############################################################
######################## GAME TRIMMING ########################
###############################################################

def trim_games(df):

    cleaned_rows = []

    grouped = df.groupby(["game_date", "away_team", "home_team"])

    for _, game_df in grouped:

        totals = game_df[game_df["market_type"] == "total"].copy()

        sides = game_df[
            game_df["market_type"].isin(["spread", "moneyline"])
        ].copy()

        best_total = None
        best_side = None

        ###################################################
        # SELECT BEST TOTAL
        ###################################################

        if not totals.empty:

            totals["edge"] = totals.apply(compute_edge, axis=1)

            best_total = totals.sort_values(
                "edge",
                ascending=False
            ).iloc[0]

        ###################################################
        # SELECT BEST SIDE
        ###################################################

        if not sides.empty:

            sides["edge"] = sides.apply(compute_edge, axis=1)

            best_side = sides.sort_values(
                "edge",
                ascending=False
            ).iloc[0]

        ###################################################
        # STORE RESULTS
        ###################################################

        if best_side is not None:
            cleaned_rows.append(best_side)

        if best_total is not None:
            cleaned_rows.append(best_total)

    if not cleaned_rows:
        return pd.DataFrame()

    return pd.DataFrame(cleaned_rows)


###############################################################
######################## TOTAL HISTORY ########################
###############################################################

def build_totals():

    nba_files = []
    ncaab_files = []

    for f in OUTPUT_DIR.glob("*.csv"):

        name = f.name

        # Skip master files
        if name in ["nba_selected.csv", "ncaab_selected.csv"]:
            continue

        if name.endswith("_nba.csv"):
            nba_files.append(f)

        if name.endswith("_ncaab.csv"):
            ncaab_files.append(f)

    ###################################################
    # NBA HISTORY
    ###################################################

    if nba_files:

        nba_dfs = [pd.read_csv(f) for f in sorted(nba_files)]

        nba_final = pd.concat(nba_dfs, ignore_index=True)

        nba_final.to_csv(
            TOTALS_DIR / "NBA_final.csv",
            index=False
        )

    ###################################################
    # NCAAB HISTORY
    ###################################################

    if ncaab_files:

        ncaab_dfs = [pd.read_csv(f) for f in sorted(ncaab_files)]

        ncaab_final = pd.concat(ncaab_dfs, ignore_index=True)

        ncaab_final.to_csv(
            TOTALS_DIR / "NCAAB_final.csv",
            index=False
        )

    print("Totals history files created.")


###############################################################
######################## MAIN PIPELINE ########################
###############################################################

def main():

    ###################################################
    # CLEAR OLD DAILY SLATE FILES
    ###################################################

    for f in OUTPUT_DIR.glob("*.csv"):
        f.unlink()

    ###################################################
    # LOAD SELECT FILES
    ###################################################

    files = [
        f for f in SELECT_DIR.glob("*.csv")
        if f.name not in ["nba_selected.csv", "ncaab_selected.csv"]
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

    ###################################################
    # COMBINE DATA
    ###################################################

    df = pd.concat(dfs, ignore_index=True)

    ###################################################
    # SPLIT BY LEAGUE
    ###################################################

    nba_df = df[df["market"].str.contains("NBA", na=False)]

    ncaab_df = df[df["market"].str.contains("NCAAB", na=False)]

    ###################################################
    # TRIM BETS
    ###################################################

    nba_trimmed = trim_games(nba_df)

    ncaab_trimmed = trim_games(ncaab_df)

    ###################################################
    # MASTER FILES
    ###################################################

    nba_master = OUTPUT_DIR / "nba_selected.csv"
    ncaab_master = OUTPUT_DIR / "ncaab_selected.csv"

    nba_trimmed.to_csv(nba_master, index=False)
    ncaab_trimmed.to_csv(ncaab_master, index=False)

    print(f"NBA master file created: {nba_master}")
    print(f"NCAAB master file created: {ncaab_master}")

    ###################################################
    # DAILY SLATE FILES
    ###################################################

    for date, g in nba_trimmed.groupby("game_date"):

        path = OUTPUT_DIR / f"{date}_nba.csv"

        g.to_csv(path, index=False)

    for date, g in ncaab_trimmed.groupby("game_date"):

        path = OUTPUT_DIR / f"{date}_ncaab.csv"

        g.to_csv(path, index=False)

    print("Daily slate files created.")

    ###################################################
    # BUILD TOTAL HISTORY
    ###################################################

    build_totals()


###############################################################

if __name__ == "__main__":
    main()
