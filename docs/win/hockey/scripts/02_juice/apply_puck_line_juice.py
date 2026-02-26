# docs/win/hockey/scripts/02_juice/apply_puck_line_juice.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

INPUT_FILE = Path("docs/win/hockey/01_merge/2026_02_26_NHL_puck_line.csv")
OUTPUT_FILE = Path("docs/win/hockey/02_juice/2026_02_26_NHL_puck_line.csv")
JUICE_FILE = Path("config/hockey/nhl/nhl_puck_line_juice.csv")


def find_band_row(juice_df, puck_line, venue):
    band_low = juice_df[["band_min", "band_max"]].min(axis=1)
    band_high = juice_df[["band_min", "band_max"]].max(axis=1)

    band = juice_df[
        (band_low <= puck_line) &
        (puck_line <= band_high) &
        (juice_df["venue"] == venue)
    ]

    if band.empty:
        return None

    return float(band.iloc[0]["extra_juice"])


def process_side(df, juice_df, side):
    puck_col = f"{side}_puck_line"
    fair_col = f"{side}_fair_puck_line_decimal"

    juiced_decimal_col = f"{side}_juiced_decimal_puck_line"
    juiced_prob_col = f"{side}_juiced_prob_puck_line"

    df[juiced_decimal_col] = None
    df[juiced_prob_col] = None

    for idx, row in df.iterrows():
        puck_line = float(row[puck_col])
        fair_decimal = float(row[fair_col])

        extra = find_band_row(juice_df, puck_line, side)
        if extra is None:
            continue

        juiced_decimal = fair_decimal + extra
        juiced_prob = 1 / juiced_decimal

        df.at[idx, juiced_decimal_col] = juiced_decimal
        df.at[idx, juiced_prob_col] = juiced_prob

    return df


def main():
    juice_df = pd.read_csv(JUICE_FILE)
    juice_df["band_min"] = juice_df["band_min"].astype(float)
    juice_df["band_max"] = juice_df["band_max"].astype(float)
    juice_df["venue"] = juice_df["venue"].str.strip()

    df = pd.read_csv(INPUT_FILE)

    df = process_side(df, juice_df, "home")
    df = process_side(df, juice_df, "away")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
