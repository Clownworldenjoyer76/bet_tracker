# docs/win/basketball/scripts/model_testing/compute_edges.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import re

INPUT_DIR = Path("docs/win/basketball/02_juice")
OUTPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OPTIMIZER_DATASET = Path(
    "docs/win/basketball/model_testing/optimizer_base_dataset.csv"
)

all_rows = []


def implied_prob(decimal):
    return (1 / decimal).where(decimal > 1, 0)


def edge(model, book):
    model = pd.to_numeric(model, errors="coerce")
    book = pd.to_numeric(book, errors="coerce")
    return implied_prob(model) - implied_prob(book)


def extract_date(name):
    return re.search(r"\d{4}_\d{2}_\d{2}", name).group(0)


def compute_moneyline(df):

    df["home_edge_decimal"] = edge(
        df["home_dk_decimal_moneyline"],
        df["home_juice_decimal_moneyline"]
    )

    df["away_edge_decimal"] = edge(
        df["away_dk_decimal_moneyline"],
        df["away_juice_decimal_moneyline"]
    )

    return df


def compute_spread(df):

    df["home_edge_decimal"] = edge(
        df["home_dk_spread_decimal"],
        df["home_spread_juice_decimal"]
    )

    df["away_edge_decimal"] = edge(
        df["away_dk_spread_decimal"],
        df["away_spread_juice_decimal"]
    )

    return df


def compute_total(df):

    df["over_edge_decimal"] = edge(
        df["dk_total_over_decimal"],
        df["total_over_juice_decimal"]
    )

    df["under_edge_decimal"] = edge(
        df["dk_total_under_decimal"],
        df["total_under_juice_decimal"]
    )

    return df


def build_optimizer_rows(df, league, market, date):

    rows = []

    if market == "moneyline":

        for side in ["home", "away"]:

            edge_col = f"{side}_edge_decimal"
            odds_col = f"{side}_dk_decimal_moneyline"

            if edge_col not in df.columns:
                continue

            tmp = df.copy()

            tmp["market"] = league
            tmp["market_type"] = "moneyline"
            tmp["bet_side"] = side
            tmp["candidate_edge"] = tmp[edge_col]
            tmp["take_odds"] = tmp[odds_col]
            tmp["game_date"] = date

            rows.append(tmp)

    elif market == "spread":

        for side in ["home", "away"]:

            edge_col = f"{side}_edge_decimal"
            odds_col = f"{side}_dk_spread_decimal"

            if edge_col not in df.columns:
                continue

            tmp = df.copy()

            tmp["market"] = league
            tmp["market_type"] = "spread"
            tmp["bet_side"] = side
            tmp["candidate_edge"] = tmp[edge_col]
            tmp["take_odds"] = tmp[odds_col]
            tmp["game_date"] = date

            rows.append(tmp)

    elif market == "total":

        for side in ["over", "under"]:

            edge_col = f"{side}_edge_decimal"
            odds_col = f"dk_total_{side}_decimal"

            if edge_col not in df.columns:
                continue

            tmp = df.copy()

            tmp["market"] = league
            tmp["market_type"] = "total"
            tmp["bet_side"] = side
            tmp["candidate_edge"] = tmp[edge_col]
            tmp["take_odds"] = tmp[odds_col]
            tmp["game_date"] = date

            rows.append(tmp)

    if rows:
        return pd.concat(rows, ignore_index=True)

    return pd.DataFrame()


def process(files, fn, league, market):

    for f in files:

        df = pd.read_csv(f)
        df = fn(df)

        date = extract_date(f.name)

        out = OUTPUT_DIR / f"{date}_basketball_{league}_{market}.csv"
        df.to_csv(out, index=False)

        # Build optimizer rows
        opt_rows = build_optimizer_rows(df, league, market, date)

        if not opt_rows.empty:
            all_rows.append(opt_rows)


def main():

    process(INPUT_DIR.glob("*_NBA_moneyline.csv"), compute_moneyline, "NBA", "moneyline")
    process(INPUT_DIR.glob("*_NBA_spread.csv"), compute_spread, "NBA", "spread")
    process(INPUT_DIR.glob("*_NBA_total.csv"), compute_total, "NBA", "total")

    process(INPUT_DIR.glob("*_NCAAB_moneyline.csv"), compute_moneyline, "NCAAB", "moneyline")
    process(INPUT_DIR.glob("*_NCAAB_spread.csv"), compute_spread, "NCAAB", "spread")
    process(INPUT_DIR.glob("*_NCAAB_total.csv"), compute_total, "NCAAB", "total")

    if all_rows:

        optimizer_df = pd.concat(all_rows, ignore_index=True)

        OPTIMIZER_DATASET.parent.mkdir(parents=True, exist_ok=True)
        optimizer_df.to_csv(OPTIMIZER_DATASET, index=False)

        print("Optimizer dataset written:", OPTIMIZER_DATASET)
        print("Rows:", len(optimizer_df))


if __name__ == "__main__":
    main()
