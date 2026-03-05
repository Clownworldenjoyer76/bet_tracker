#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/combine_trim_basketball.py

import pandas as pd
from pathlib import Path

SELECT_DIR = Path("docs/win/basketball/04_select")
OUTPUT_DIR = SELECT_DIR / "daily_slate"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_edge(row):
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

    cleaned = []

    for _, g in df.groupby(["game_date", "away_team", "home_team"]):

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

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if not df.empty:
                dfs.append(df)
        except:
            continue

    if not dfs:
        print("No data found.")
        return

    df = pd.concat(dfs, ignore_index=True)

    nba_df = df[df["market"].str.contains("NBA", na=False)]
    ncaab_df = df[df["market"].str.contains("NCAAB", na=False)]

    nba_final = trim_games(nba_df)
    ncaab_final = trim_games(ncaab_df)

    # master files
    nba_final.to_csv(OUTPUT_DIR / "nba_selected.csv", index=False)
    ncaab_final.to_csv(OUTPUT_DIR / "ncaab_selected.csv", index=False)

    # daily files
    for date, g in nba_final.groupby("game_date"):
        g.to_csv(OUTPUT_DIR / f"{date}_nba.csv", index=False)

    for date, g in ncaab_final.groupby("game_date"):
        g.to_csv(OUTPUT_DIR / f"{date}_ncaab.csv", index=False)


if name == "main":
    main()
