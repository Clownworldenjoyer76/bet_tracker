#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/combine_trim_basketball.py

import pandas as pd
from pathlib import Path

SELECT_DIR = Path("docs/win/basketball/04_select")
OUTPUT_DIR = SELECT_DIR / "daily_slate"
TOTALS_DIR = OUTPUT_DIR / "totals"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_DIR.mkdir(parents=True, exist_ok=True)


def compute_edge(row):
    """Return the relevant edge used for ranking bets"""
    if row["market_type"] == "total":
        return max(
            float(row.get("over_edge_decimal", 0) or 0),
            float(row.get("under_edge_decimal", 0) or 0),
        )
    else:
        return max(
            float(row.get("home_edge_decimal", 0) or 0),
            float(row.get("away_edge_decimal", 0) or 0),
        )


def trim_games(df):
    """
    Enforce betting rules per game:
    - Maximum 2 bets per game
    - Only ONE of: spread OR moneyline
    - Only ONE of: over OR under
    """

    cleaned_rows = []

    grouped = df.groupby(["game_date", "away_team", "home_team"])

    for _, game_df in grouped:

        totals = game_df[game_df["market_type"] == "total"].copy()
        sides = game_df[game_df["market_type"].isin(["spread", "moneyline"])].copy()

        best_total = None
        best_side = None

        if not totals.empty:
            totals["edge"] = totals.apply(compute_edge, axis=1)
            best_total = totals.sort_values("edge", ascending=False).iloc[0]

        if not sides.empty:
            sides["edge"] = sides.apply(compute_edge, axis=1)
            best_side = sides.sort_values("edge", ascending=False).iloc[0]

        if best_side is not None:
            cleaned_rows.append(best_side)

        if best_total is not None:
            cleaned_rows.append(best_total)

    if not cleaned_rows:
        return pd.DataFrame()

    return pd.DataFrame(cleaned_rows)


def build_totals():
    """
    Combine all daily slate files into master history files.
    Excludes nba_selected.csv and ncaab_selected.csv.
    """

    nba_files = []
    ncaab_files = []

    for f in OUTPUT_DIR.glob("*.csv"):

        name = f.name

        if name in ["nba_selected.csv", "ncaab_selected.csv"]:
            continue

        if name.endswith("_nba.csv"):
            nba_files.append(f)

        if name.endswith("_ncaab.csv"):
            ncaab_files.append(f)

    if nba_files:
        nba_dfs = [pd.read_csv(f) for f in sorted(nba_files)]
        nba_final = pd.concat(nba_dfs, ignore_index=True)
        nba_final.to_csv(TOTALS_DIR / "NBA_final.csv", index=False)

    if ncaab_files:
        ncaab_dfs = [pd.read_csv(f) for f in sorted(ncaab_files)]
        ncaab_final = pd.concat(ncaab_dfs, ignore_index=True)
        ncaab_final.to_csv(TOTALS_DIR / "NCAAB_final.csv", index=False)

    print("Totals files created.")


def main():

    files = list(SELECT_DIR.glob("*.csv"))

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

    nba_df = df[df["market"].str.contains("NBA", na=False)]
    ncaab_df = df[df["market"].str.contains("NCAAB", na=False)]

    nba_trimmed = trim_games(nba_df)
    ncaab_trimmed = trim_games(ncaab_df)

    # MASTER FILES
    nba_master = OUTPUT_DIR / "nba_selected.csv"
    ncaab_master = OUTPUT_DIR / "ncaab_selected.csv"

    nba_trimmed.to_csv(nba_master, index=False)
    ncaab_trimmed.to_csv(ncaab_master, index=False)

    print(f"NBA master: {nba_master}")
    print(f"NCAAB master: {ncaab_master}")

    # DAILY FILES
    for date, g in nba_trimmed.groupby("game_date"):
        path = OUTPUT_DIR / f"{date}_nba.csv"
        g.to_csv(path, index=False)

    for date, g in ncaab_trimmed.groupby("game_date"):
        path = OUTPUT_DIR / f"{date}_ncaab.csv"
        g.to_csv(path, index=False)

    print("Daily slate files created.")

    # BUILD TOTAL HISTORY FILES
    build_totals()


if __name__ == "__main__":
    main()
