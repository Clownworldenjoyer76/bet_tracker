#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import traceback
from datetime import datetime
import sys

INPUT_DIR = Path("docs/win/soccer/01_merge")
OUTPUT_DIR = Path("docs/win/soccer/02_juice")

ERROR_DIR = Path("docs/win/soccer/errors/02_juice")
ERROR_LOG = ERROR_DIR / "01_apply_juice.txt"

JUICE_MAP = {
    "epl": Path("config/soccer/epl/epl_1x2_juice.csv"),
    "laliga": Path("config/soccer/la_liga/laliga_1x2_juice.csv"),
    "bundesliga": Path("config/soccer/bundesliga/bundesliga_1x2_juice.csv"),
    "ligue1": Path("config/soccer/ligue1/ligue1_1x2_juice.csv"),
    "seriea": Path("config/soccer/serie_a/seriea_1x2_juice.csv"),
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def decimal_to_american(d):
    if pd.isna(d) or d <= 1:
        return ""
    if d >= 2.0:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


def find_band(prob, juice_df):
    band = juice_df[
        (juice_df["band_min"] <= prob) &
        (prob < juice_df["band_max"])
    ]
    if band.empty:
        raise ValueError(f"No juice band found for probability {prob}")
    return band.iloc[0]


def main():

    with open(ERROR_LOG, "w") as log:

        log.write("=== APPLY JUICE RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:
            files = glob.glob(str(INPUT_DIR / "soccer_*.csv"))
            if not files:
                log.write("No input files found.\n")
                return

            total_rows = 0

            for file_path in files:
                df = pd.read_csv(file_path)

                if "market" not in df.columns:
                    raise ValueError("Missing 'market' column")

                for market in df["market"].unique():
                    if market not in JUICE_MAP:
                        raise ValueError(f"No juice config mapped for market: {market}")

                juice_tables = {
                    m: pd.read_csv(JUICE_MAP[m])
                    for m in df["market"].unique()
                }

                for side in ["home", "draw", "away"]:

                    prob_col = f"{side}_prob"

                    df[f"{side}_fair_decimal"] = ""
                    df[f"{side}_adjusted_decimal"] = ""
                    df[f"{side}_adjusted_american"] = ""

                    for idx, row in df.iterrows():

                        prob = row[prob_col]

                        if pd.isna(prob) or prob <= 0 or prob >= 1:
                            continue

                        market = row["market"]
                        juice_df = juice_tables[market]

                        fair_decimal = 1 / prob
                        band_row = find_band(prob, juice_df)
                        adjusted_prob = min(prob + band_row["extra_juice"], 0.999)

                        adjusted_decimal = 1 / adjusted_prob
                        adjusted_american = decimal_to_american(adjusted_decimal)

                        df.at[idx, f"{side}_fair_decimal"] = fair_decimal
                        df.at[idx, f"{side}_adjusted_decimal"] = adjusted_decimal
                        df.at[idx, f"{side}_adjusted_american"] = adjusted_american

                        total_rows += 1

                output_path = OUTPUT_DIR / Path(file_path).name
                df.to_csv(output_path, index=False)
                log.write(f"Wrote {output_path}\n")

            log.write("\n=== SUMMARY ===\n")
            log.write(f"Rows processed: {total_rows}\n")

        except Exception:
            log.write("\n=== ERROR ===\n")
            log.write(traceback.format_exc())

    # Always exit 0 so workflow can commit log
    sys.exit(0)


if __name__ == "__main__":
    main()
