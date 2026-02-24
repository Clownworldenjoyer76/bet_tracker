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
JUICE_FILE = Path("config/hockey/nhl/nhl_puck_runline_bands.csv")

ERROR_DIR = Path("docs/win/hockey/errors/02_juice")
LOG_FILE = ERROR_DIR / "apply_puck_line_juice.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def find_row(juice_df, fav_ud, venue):
    band = juice_df[
        (juice_df["band"] == "1 to 1.5") &
        (juice_df["fav_ud"] == fav_ud) &
        (juice_df["venue"] == venue)
    ]
    if band.empty:
        return None
    return band.iloc[0]


def apply_side(df, side, juice_df):
    dk_col = f"{side}_dk_puck_line_decimal"
    puck_col = f"{side}_puck_line"

    df[f"{side}_juiced_prob_puck_line"] = pd.NA
    df[f"{side}_juiced_decimal_puck_line"] = pd.NA

    for idx, row in df.iterrows():
        try:
            puck_line_value = float(row[puck_col])
        except Exception:
            continue

        # Determine favorite/underdog strictly by puck line sign
        if puck_line_value == -1.5:
            fav_ud = "favorite"
        elif puck_line_value == 1.5:
            fav_ud = "underdog"
        else:
            continue

        venue = side

        band_row = find_row(juice_df, fav_ud, venue)

        if band_row is None:
            continue

        juiced_prob = float(band_row["win_pct"])
        juiced_decimal = 1 / juiced_prob if juiced_prob > 0 else pd.NA

        df.at[idx, f"{side}_juiced_prob_puck_line"] = juiced_prob
        df.at[idx, f"{side}_juiced_decimal_puck_line"] = juiced_decimal

    return df


def main():
    with open(LOG_FILE, "w") as log:
        log.write(f"=== APPLY PUCK LINE JUICE {datetime.utcnow().isoformat()}Z ===\n\n")

    try:
        juice_df = pd.read_csv(JUICE_FILE)
        files = glob.glob(str(INPUT_DIR / "*_NHL_puck_line.csv"))

        if not files:
            with open(LOG_FILE, "a") as log:
                log.write("No NHL puck line files found\n")
            return

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
