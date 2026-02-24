# docs/win/hockey/scripts/02_juice/apply_total_juice.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
from datetime import datetime
import traceback
import sys

INPUT_DIR = Path("docs/win/hockey/01_merge")
OUTPUT_DIR = Path("docs/win/hockey/02_juice")
JUICE_FILE = Path("config/hockey/nhl/nhl_total_juice.csv")

ERROR_DIR = Path("docs/win/hockey/errors/02_juice")
LOG_FILE = ERROR_DIR / "apply_total_juice.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def find_band(juice_df, total, side):
    band = juice_df[
        (juice_df["band_min"] <= total) &
        (total < juice_df["band_max"]) &
        (juice_df["side"] == side)
    ]
    if band.empty:
        raise ValueError(f"No total juice band for {total}, {side}")
    return band.iloc[0]["extra_juice"]


def apply_side(df, side, juice_df):
    fair_col = f"fair_total_{side}_decimal"

    df[f"juiced_total_{side}_prob"] = pd.NA
    df[f"juiced_total_{side}_decimal"] = pd.NA

    for idx, row in df.iterrows():
        total = float(row["total"])
        fair_decimal = float(row[fair_col])

        extra_juice = find_band(juice_df, total, side)

        fair_prob = 1 / fair_decimal
        juiced_prob = fair_prob + extra_juice
        juiced_prob = min(0.999, max(0.000001, juiced_prob))

        juiced_decimal = 1 / juiced_prob

        df.at[idx, f"juiced_total_{side}_prob"] = juiced_prob
        df.at[idx, f"juiced_total_{side}_decimal"] = juiced_decimal

    return df


def main():
    with open(LOG_FILE, "w") as log:
        log.write(f"=== APPLY TOTAL JUICE {datetime.utcnow().isoformat()}Z ===\n\n")

    try:
        juice_df = pd.read_csv(JUICE_FILE)
        files = glob.glob(str(INPUT_DIR / "*_NHL_total.csv"))

        for file_path in files:
            df = pd.read_csv(file_path)

            df = apply_side(df, "over", juice_df)
            df = apply_side(df, "under", juice_df)

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
