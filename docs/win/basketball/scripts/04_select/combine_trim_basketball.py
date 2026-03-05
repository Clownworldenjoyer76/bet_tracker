#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/combine_trim_basketball.py

import pandas as pd
from pathlib import Path

SELECT_DIR = Path("docs/win/basketball/04_select")


def compute_edge(row):
    """Return the relevant edge for ranking bets"""
    if row["market_type"] == "total":
        return max(
            float(row.get("over_edge_decimal", 0) or 0),
            float(row.get("under_edge_decimal", 0) or 0)
        )
    else:
        return max(
            float(row.get("home_edge_decimal", 0) or 0),
            float(row.get("away_edge_decimal", 0) or 0)
        )


def trim_games(df):

    cleaned = []

    for game, g in df.groupby(["game_date", "away_team", "home_team"]):

        totals = g[g.market_type == "total"].copy()
        sides = g[g.market_type.isin(["spread", "moneyline"])].copy()

        best_total = None
        best_side = None

        if not totals.empty:
            totals["edge"] = totals.apply(compute_edge, axis=1)
            best_total = totals.sort_values("edge", ascending=False).iloc[0]

        if not sides.empty:
            sides["edge"] = sides.apply(compute_edge, axis=1)
            best_side = sides.sort_values("edge", ascending=False).iloc[0]

        if best_side is not None:
            cleaned.append(best_side)

        if best_total is not None:
            cleaned.append(best_total)

    return pd.DataFrame(cleaned)


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

    nba_final = trim_games(nba_df)
    ncaab_final = trim_games(ncaab_df)

    nba_out = SELECT_DIR / "nba_selected.csv"
    ncaab_out = SELECT_DIR / "ncaab_selected.csv"

    nba_final.to_csv(nba_out, index=False)
    ncaab_final.to_csv(ncaab_out, index=False)

    print(f"NBA bets: {len(nba_final)} → {nba_out}")
    print(f"NCAAB bets: {len(ncaab_final)} → {ncaab_out}")


if __name__ == "__main__":
    main()
