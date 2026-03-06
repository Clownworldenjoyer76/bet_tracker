# docs/win/basketball/scripts/model_testing/combine_trim_basketball.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

SELECT_DIR = Path("docs/win/basketball/04_select")

def edge(row):

    if row["market_type"] == "total":
        return max(
            float(row.get("over_edge_decimal", 0) or 0),
            float(row.get("under_edge_decimal", 0) or 0)
        )

    return max(
        float(row.get("home_edge_decimal", 0) or 0),
        float(row.get("away_edge_decimal", 0) or 0)
    )

def trim(df):

    rows = []

    for _, g in df.groupby(["game_date","away_team","home_team"]):

        totals = g[g.market_type == "total"]
        sides = g[g.market_type.isin(["spread","moneyline"])]

        if not totals.empty:
            totals = totals.copy()
            totals["edge"] = totals.apply(edge, axis=1)
            rows.append(totals.sort_values("edge", ascending=False).iloc[0])

        if not sides.empty:
            sides = sides.copy()
            sides["edge"] = sides.apply(edge, axis=1)
            rows.append(sides.sort_values("edge", ascending=False).iloc[0])

    return pd.DataFrame(rows)

def safe_read_csv(path):
    try:
        df = pd.read_csv(path)
        if df.empty or len(df.columns) == 0:
            return None
        return df
    except pd.errors.EmptyDataError:
        return None

def main():

    files = list(SELECT_DIR.glob("*.csv"))

    dfs = []
    for f in files:
        df = safe_read_csv(f)
        if df is not None:
            dfs.append(df)

    if not dfs:
        return

    df = pd.concat(dfs, ignore_index=True)

    nba = trim(df[df.market.str.contains("NBA", na=False)])
    ncaab = trim(df[df.market.str.contains("NCAAB", na=False)])

    nba.to_csv(SELECT_DIR / "nba_selected.csv", index=False)
    ncaab.to_csv(SELECT_DIR / "ncaab_selected.csv", index=False)

if __name__ == "__main__":
    main()
