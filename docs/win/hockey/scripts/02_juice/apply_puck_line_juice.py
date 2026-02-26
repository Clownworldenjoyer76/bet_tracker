# docs/win/hockey/scripts/02_juice/apply_puck_line_juice.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
from datetime import datetime
import traceback
import sys

INPUT_DIR = Path("docs/win/hockey/01_merge")
OUTPUT_DIR = Path("docs/win/hockey/02_juice")
JUICE_FILE = Path("config/hockey/nhl/nhl_puck_line_juice.csv")

ERROR_DIR = Path("docs/win/hockey/errors/02_juice")
LOG_FILE = ERROR_DIR / "apply_puck_line_juice.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def find_band_row(juice_df, puck_line, venue):
    band = juice_df[
        (
            (
                (juice_df["band_min"] <= puck_line) &
                (puck_line <= juice_df["band_max"])
            ) |
            (
                (juice_df["band_max"] <= puck_line) &
                (puck_line <= juice_df["band_min"])
            )
        ) &
        (juice_df["venue"] == venue)
    ]

    if band.empty:
        raise ValueError(f"No puck line juice band for {puck_line}, {venue}")

    return float(band.iloc[0]["extra_juice"])


def process_side(df, juice_df, side):
    puck_col = f"{side}_puck_line"
    fair_col = f"{side}_fair_puck_line_decimal"

    juiced_decimal_col = f"{side}_juiced_decimal_puck_line"
    juiced_prob_col = f"{side}_juiced_prob_puck_line"

    df[juiced_decimal_col] = pd.NA
    df[juiced_prob_col] = pd.NA

    for idx, row in df.iterrows():
        puck_line = round(float(row[puck_col]), 1)
        fair_decimal = float(row[fair_col])

        extra = find_band_row(juice_df, puck_line, side)

        juiced_decimal = fair_decimal + extra
        juiced_prob = 1 / juiced_decimal

        df.at[idx, juiced_decimal_col] = juiced_decimal
        df.at[idx, juiced_prob_col] = juiced_prob

    return df


def main():
    with open(LOG_FILE, "w") as log:
        log.write(f"=== APPLY PUCK LINE JUICE {datetime.utcnow().isoformat()}Z ===\n\n")

    try:
        juice_df = pd.read_csv(JUICE_FILE)

        juice_df["band_min"] = juice_df["band_min"].astype(float)
        juice_df["band_max"] = juice_df["band_max"].astype(float)
        juice_df["venue"] = juice_df["venue"].str.strip()

        files = glob.glob(str(INPUT_DIR / "*_NHL_puck_line.csv"))

        if not files:
            raise ValueError("No NHL puck line files found")

        for file_path in files:
            df = pd.read_csv(file_path)

            df = process_side(df, juice_df, "home")
            df = process_side(df, juice_df, "away")

            output_path = OUTPUT_DIR / Path(file_path).name
            df.to_csv(output_path, index=False)

            with open(LOG_FILE, "a") as log:
                log.write(f"Wrote {output_path}\n")

    except Exception as e:
        with open(LOG_FILE, "a") as log:
            log.write("\nERROR\n")
            log.write(str(e) + "\n")
            log.write(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
