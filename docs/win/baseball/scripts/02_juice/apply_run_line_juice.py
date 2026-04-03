#!/usr/bin/env python3

import glob
from pathlib import Path
import pandas as pd

INPUT_DIR = Path("docs/win/baseball/01_merge")
OUTPUT_DIR = Path("docs/win/baseball/02_juice")
JUICE_FILE = Path("docs/win/baseball/config/mlb_run_line_juice_scaled.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_band(df, odds, venue, fav_ud):
    band = df[
        (df["band_min"] <= odds) &
        (df["band_max"] > odds) &
        (df["venue"] == venue) &
        (df["fav_ud"] == fav_ud)
    ]
    if band.empty:
        return 0.0
    return float(band.iloc[0]["extra_juice"])


def process(df, juice_df):

    df["home_juiced_prob_run_line"] = None
    df["away_juiced_prob_run_line"] = None

    df["home_normalized_prob_run_line"] = None
    df["away_normalized_prob_run_line"] = None

    for i, row in df.iterrows():

        try:
            home_base = float(row["home_run_line_prob"])
            away_base = float(row["away_run_line_prob"])

            home_odds = float(row["home_dk_run_line_american"])
            away_odds = float(row["away_dk_run_line_american"])
        except:
            continue

        home_type = "favorite" if home_odds < 0 else "underdog"
        away_type = "favorite" if away_odds < 0 else "underdog"

        home_extra = find_band(juice_df, home_odds, "home", home_type)
        away_extra = find_band(juice_df, away_odds, "away", away_type)

        # PURE ADDITIVE ADJUSTMENT (NO SCALING, NO NORMALIZATION)
        home_final = home_base + home_extra
        away_final = away_base + away_extra

        # LIGHT SAFETY BOUNDS ONLY (no distortion)
        home_final = max(min(home_final, 0.75), 0.05)
        away_final = max(min(away_final, 0.75), 0.05)

        df.at[i, "home_juiced_prob_run_line"] = home_final
        df.at[i, "away_juiced_prob_run_line"] = away_final

        df.at[i, "home_normalized_prob_run_line"] = home_final
        df.at[i, "away_normalized_prob_run_line"] = away_final

    return df


def main():

    juice_df = pd.read_csv(JUICE_FILE)
    files = sorted(glob.glob(str(INPUT_DIR / "*_mlb_run_line.csv")))

    for file in files:
        df = pd.read_csv(file)
        df = process(df, juice_df)
        df.to_csv(OUTPUT_DIR / Path(file).name, index=False)


if __name__ == "__main__":
    main()