# docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import math

INPUT_DIR = Path("docs/win/basketball/01_merge")
OUTPUT_DIR = Path("docs/win/basketball/02_juice")

NBA_CONFIG = Path("config/nba/nba_ml_juice.csv")
NCAAB_CONFIG = Path("config/ncaab/ncaab_ml_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def american_to_decimal(a):
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def decimal_to_american(d):
    if not math.isfinite(d) or d <= 1:
        return ""
    if d >= 2:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


def apply_nba_ml(df, jt):

    jt = jt[jt["lookup_type"] == "band"].copy()

    def process_row(row, side):

        col = f"{side}_acceptable_american_moneyline"

        if col not in row:
            return ""

        odds = row[col]
        if pd.isna(odds):
            return ""

        odds = float(odds)

        fav_ud = "favorite" if odds < 0 else "underdog"

        band = jt[
            (jt["band_min"] <= odds) &
            (odds <= jt["band_max"]) &
            (jt["fav_ud"] == fav_ud) &
            (jt["venue"] == side)
        ]

        if band.empty:
            return odds

        extra = band.iloc[0]["extra_juice"]
        if not math.isfinite(extra):
            extra = 2.0

        base_dec = american_to_decimal(odds)
        new_dec = base_dec * (1 + extra)

        return decimal_to_american(new_dec)

    for side in ["home", "away"]:
        df[f"{side}_juice_odds"] = df.apply(lambda r: process_row(r, side), axis=1)

    return df


def apply_ncaab_ml(df, jt):

    def lookup(prob):
        band = jt[(jt["prob_bin_min"] <= prob) & (prob < jt["prob_bin_max"])]
        return 0 if band.empty else band.iloc[0]["extra_juice"]

    def process_row(row, side):

        prob = float(row[f"{side}_prob"])
        odds = float(row[f"{side}_acceptable_american_moneyline"])

        extra = lookup(prob)

        base_dec = american_to_decimal(odds)
        new_dec = base_dec * (1 + extra)

        return decimal_to_american(new_dec)

    for side in ["home", "away"]:
        df[f"{side}_juice_odds"] = df.apply(lambda r: process_row(r, side), axis=1)

    return df


def main():

    files = glob.glob(str(INPUT_DIR / "*.csv"))

    for f in files:

        df = pd.read_csv(f)
        date = df["game_date"].iloc[0]

        nba_df = df[df["market"] == "NBA"].copy()
        ncaab_df = df[df["market"] == "NCAAB"].copy()

        if not nba_df.empty:
            nba_df = apply_nba_ml(nba_df, pd.read_csv(NBA_CONFIG))
            nba_df.to_csv(OUTPUT_DIR / f"{date}_NBA_moneyline.csv", index=False)

        if not ncaab_df.empty:
            ncaab_df = apply_ncaab_ml(ncaab_df, pd.read_csv(NCAAB_CONFIG))
            ncaab_df.to_csv(OUTPUT_DIR / f"{date}_NCAAB_moneyline.csv", index=False)


if __name__ == "__main__":
    main()
