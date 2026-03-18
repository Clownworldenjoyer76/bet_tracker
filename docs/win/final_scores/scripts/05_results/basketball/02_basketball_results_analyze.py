#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

NBA_INPUT = Path("docs/win/final_scores/results/nba/graded/NBA_final.csv")
NCAAB_INPUT = Path("docs/win/final_scores/results/ncaab/graded/NCAAB_final.csv")

OUTPUT_DIR = Path("docs/win/final_scores/intermediate")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_col(row, base):
    # try clean → _x → _y
    for c in [base, f"{base}_x", f"{base}_y"]:
        if c in row:
            return row[c]
    return None


def prepare(df, league):

    df["market"] = league
    df["market_type"] = df["market_type"].str.lower()

    def side_group(row):
        if row["market_type"] in ["moneyline","spread"]:
            return "HOME" if row["bet_side"] == "home" else "AWAY"
        if row["market_type"] == "total":
            return "OVER" if row["bet_side"] == "over" else "UNDER"
        return ""

    df["side_group"] = df.apply(side_group, axis=1)

    def edge(row):

        if row["market_type"] == "moneyline":
            if row["side_group"] == "HOME":
                return get_col(row, "home_ml_edge")
            else:
                return get_col(row, "away_ml_edge")

        if row["market_type"] == "spread":
            if row["side_group"] == "HOME":
                return get_col(row, "home_spread_edge")
            else:
                return get_col(row, "away_spread_edge")

        if row["market_type"] == "total":
            if row["side_group"] == "OVER":
                return get_col(row, "over_edge")
            else:
                return get_col(row, "under_edge")

        return None

    df["selected_edge"] = df.apply(edge, axis=1)

    def edge_bucket(x):
        if pd.isna(x): return "NA"
        if x < 0.01: return "0-1%"
        if x < 0.03: return "1-3%"
        if x < 0.05: return "3-5%"
        if x < 0.10: return "5-10%"
        return "10%+"

    df["edge_bucket"] = df["selected_edge"].apply(edge_bucket)

    return df


def run():
    nba = pd.read_csv(NBA_INPUT)
    ncaab = pd.read_csv(NCAAB_INPUT)

    nba = prepare(nba, "NBA")
    ncaab = prepare(ncaab, "NCAAB")

    nba.to_csv(OUTPUT_DIR / "work_nba.csv", index=False)
    ncaab.to_csv(OUTPUT_DIR / "work_ncaab.csv", index=False)

    print("Analyze complete.")


if __name__ == "__main__":
    run()