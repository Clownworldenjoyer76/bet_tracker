# docs/win/basketball/scripts/02_juice/apply_total_juice.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import math

INPUT_DIR = Path("docs/win/basketball/01_merge")
OUTPUT_DIR = Path("docs/win/basketball/02_juice")

NBA_CONFIG = Path("config/nba/nba_totals_juice.csv")
NCAAB_CONFIG = Path("config/ncaab/ncaab_totals_juice.csv")

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
        # NBA TOTAL
        # =========================
        if not nba_df.empty:

            jt = pd.read_csv(NBA_CONFIG)

            def nba_row(row, side):

                total = float(row["total"])
                odds = float(row[f"acceptable_total_{side}_american"])

                band = jt[
                    (jt["band_min"] <= total) &
                    (total < jt["band_max"]) &
                    (jt["side"] == side)
                ]

                if band.empty:
                    return odds

                extra = band.iloc[0]["extra_juice"]
                if not math.isfinite(extra):
                    extra = 2.0

                base_dec = american_to_decimal(odds)
                return decimal_to_american(base_dec * (1 + extra))

            for side in ["over", "under"]:
                nba_df[f"{side}_total_juice_odds"] = nba_df.apply(
                    lambda r: nba_row(r, side), axis=1
                )

            nba_df.to_csv(
                OUTPUT_DIR / f"{date}_NBA_total.csv",
                index=False
            )

        # =========================
        # NCAAB TOTAL
        # =========================
        if not ncaab_df.empty:

            jt = pd.read_csv(NCAAB_CONFIG)

            def ncaab_row(row, side):

                total = float(row["total"])  # preserve .5
                odds = float(row[f"acceptable_total_{side}_american"])

                band = jt[
                    (jt["over_under"] == total) &
                    (jt["side"] == side)
                ]

                if band.empty:
                    return odds

                extra = band.iloc[0]["extra_juice"]
                if not math.isfinite(extra):
                    extra = 2.0

                base_dec = american_to_decimal(odds)
                return decimal_to_american(base_dec * (1 + extra))

            for side in ["over", "under"]:
                ncaab_df[f"{side}_total_juice_odds"] = ncaab_df.apply(
                    lambda r: ncaab_row(r, side), axis=1
                )

            ncaab_df.to_csv(
                OUTPUT_DIR / f"{date}_NCAAB_total.csv",
                index=False
            )


if __name__ == "__main__":
    main()
