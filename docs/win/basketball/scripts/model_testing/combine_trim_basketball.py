#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/combine_trim_basketball.py

from pathlib import Path

import pandas as pd

SELECT_FILE = Path("docs/win/basketball/04_select/selected_bets.csv")
SELECT_DIR = Path("docs/win/basketball/04_select")


def edge(row):
    return float(row.get("candidate_edge", 0) or 0)


def trim(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    rows = []

    grouped = df.groupby(["game_date", "away_team", "home_team"], dropna=False)

    for _, group in grouped:
        totals = group[group.market_type == "total"].copy()
        sides = group[group.market_type.isin(["spread", "moneyline"])].copy()

        if not totals.empty:
            totals["edge"] = totals.apply(edge, axis=1)
            rows.append(
                totals.sort_values(["edge", "take_odds"], ascending=[False, False]).iloc[0]
            )

        if not sides.empty:
            sides["edge"] = sides.apply(edge, axis=1)
            rows.append(
                sides.sort_values(["edge", "take_odds"], ascending=[False, False]).iloc[0]
            )

    return pd.DataFrame(rows).drop(columns=["edge"], errors="ignore")


def main():
    if not SELECT_FILE.exists():
        return

    df = pd.read_csv(SELECT_FILE)
    if df.empty:
        return

    nba = trim(df[df["league"].astype(str).str.contains("NBA", na=False)])
    ncaab = trim(df[df["league"].astype(str).str.contains("NCAAB", na=False)])

    SELECT_DIR.mkdir(parents=True, exist_ok=True)
    nba.to_csv(SELECT_DIR / "nba_selected.csv", index=False)
    ncaab.to_csv(SELECT_DIR / "ncaab_selected.csv", index=False)


if __name__ == "__main__":
    main()
