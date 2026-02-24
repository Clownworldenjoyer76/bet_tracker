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


def find_juice_row(juice_df, puck_line_value, fav_ud, venue):
    band = juice_df[
        (juice_df["band_min"] <= puck_line_value) &
        (puck_line_value < juice_df["band_max"]) &
        (juice_df["fav_ud"] == fav_ud) &
        (juice_df["venue"] == venue)
    ]
    if band.empty:
        return 0.0
    return float(band.iloc[0]["extra_juice"])


def apply_side(df, side, juice_df):
    dk_col = f"{side}_dk_puck_line_decimal"
    fair_col = f"{side}_fair_puck_line_decimal"
    puck_col = f"{side}_puck_line"

    df[f"{side}_juiced_prob_puck_line"] = pd.NA
    df[f"{side}_juiced_decimal_puck_line"] = pd.NA

    for idx, row in df.iterrows():
        dk_decimal = float(row[dk_col])
        fair_decimal = float(row[fair_col])
        puck_line_value = abs(float(row[puck_col]))

        other_side = "home" if side == "away" else "away"
        other_decimal = float(row[f"{other_side}_dk_puck_line_decimal"])

        fav_ud = "favorite" if dk_decimal < other_decimal else "underdog"
        venue = side

        extra_juice = find_juice_row(juice_df, puck_line_value, fav_ud, venue)

        fair_prob = 1 / fair_decimal
        juiced_prob = fair_prob + extra_juice
        juiced_prob = min(0.999, max(0.000001, juiced_prob))

        juiced_decimal = 1 / juiced_prob

        df.at[idx, f"{side}_juiced_prob_puck_line"] = juiced_prob
        df.at[idx, f"{side}_juiced_decimal_puck_line"] = juiced_decimal

    return df


def main():
    with open(LOG_FILE, "w") as log:
        log.write(f"=== APPLY PUCK LINE JUICE {datetime.utcnow().isoformat()}Z ===\n\n")

    try:
        juice_df = pd.read_csv(JUICE_FILE)
        files = glob.glob(str(INPUT_DIR / "*_NHL_puck_line.csv"))

        for file_path in files:
            df = pd.read_csv(file_path)

            df = apply_side(df, "home", juice_df)
            df = apply_side(df, "away", juice_df)

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
