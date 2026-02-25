#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import math
from datetime import datetime

INPUT_DIR = Path("docs/win/basketball/01_merge")
OUTPUT_DIR = Path("docs/win/basketball/02_juice")
ERROR_DIR = Path("docs/win/basketball/errors/02_juice")
ERROR_LOG = ERROR_DIR / "apply_moneyline_juice.txt"

NBA_CONFIG = Path("config/nba/nba_ml_juice.csv")
NCAAB_CONFIG = Path("config/ncaab/ncaab_ml_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


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
        odds = row[f"{side}_acceptable_american_moneyline"]
        if pd.isna(odds):
            return ""

        odds = float(odds)
        venue = side
        fav_ud = "favorite" if odds < 0 else "underdog"

        band = jt[
            (jt["band_min"] <= odds) &
            (odds <= jt["band_max"]) &
            (jt["fav_ud"] == fav_ud) &
            (jt["venue"] == venue)
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
    with open(ERROR_LOG, "w") as log:
        log.write(f"Moneyline Juice Run @ {datetime.utcnow().isoformat()}Z\n")

    files = glob.glob(str(INPUT_DIR / "basketball_*.csv"))

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
