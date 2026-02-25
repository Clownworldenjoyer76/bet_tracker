# docs/win/basketball/scripts/02_juice/apply_spread_juice.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import math

INPUT_DIR = Path("docs/win/basketball/01_merge")
OUTPUT_DIR = Path("docs/win/basketball/02_juice")

NBA_CONFIG = Path("config/nba/nba_spreads_juice.csv")
NCAAB_CONFIG = Path("config/ncaab/ncaab_spreads_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def american_to_decimal(a):
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def decimal_to_american(d):
    if not math.isfinite(d) or d <= 1:
        return ""
    if d >= 2:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


def main():

    files = glob.glob(str(INPUT_DIR / "*.csv"))

    for f in files:

        df = pd.read_csv(f)
        date = df["game_date"].iloc[0]

        nba_df = df[df["market"] == "NBA"].copy()
        ncaab_df = df[df["market"] == "NCAAB"].copy()

        # =========================
        # NBA SPREAD
        # =========================
        if not nba_df.empty:

            jt = pd.read_csv(NBA_CONFIG)

            def nba_row(row, side):

                spread = float(row[f"{side}_spread"])
                odds = float(row[f"{side}_acceptable_spread_american"])

                spread_abs = abs(spread)
                fav_ud = "favorite" if spread < 0 else "underdog"

                band = jt[
                    (jt["band_min"] <= spread_abs) &
                    (spread_abs < jt["band_max"]) &
                    (jt["fav_ud"] == fav_ud) &
                    (jt["venue"] == side)
                ]

                if band.empty:
                    return odds

                extra = band.iloc[0]["extra_juice"]
                if not math.isfinite(extra):
                    extra = 2.0

                base_dec = american_to_decimal(odds)
                return decimal_to_american(base_dec * (1 + extra))

            for side in ["home", "away"]:
                nba_df[f"{side}_spread_juice_odds"] = nba_df.apply(
                    lambda r: nba_row(r, side), axis=1
                )

            nba_df.to_csv(
                OUTPUT_DIR / f"{date}_NBA_spread.csv",
                index=False
            )

        # =========================
        # NCAAB SPREAD
        # =========================
        if not ncaab_df.empty:

            jt = pd.read_csv(NCAAB_CONFIG)

            def ncaab_row(row, side):

                spread = float(row[f"{side}_spread"])
                spread = round(spread * 2) / 2  # force .5 precision

                odds = float(row[f"{side}_acceptable_spread_american"])

                band = jt[jt["spread"] == spread]

                if band.empty:
                    return odds

                extra = band.iloc[0]["extra_juice"]
                if not math.isfinite(extra):
                    extra = 2.0

                base_dec = american_to_decimal(odds)
                return decimal_to_american(base_dec * (1 + extra))

            for side in ["home", "away"]:
                ncaab_df[f"{side}_spread_juice_odds"] = ncaab_df.apply(
                    lambda r: ncaab_row(r, side), axis=1
                )

            ncaab_df.to_csv(
                OUTPUT_DIR / f"{date}_NCAAB_spread.csv",
                index=False
            )


if __name__ == "__main__":
    main()
