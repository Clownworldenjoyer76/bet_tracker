#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import traceback
from datetime import datetime

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/soccer/01_merge")
OUTPUT_DIR = Path("docs/win/soccer/02_juice")

ERROR_DIR = Path("docs/win/soccer/errors/02_juice")
ERROR_LOG = ERROR_DIR / "01_apply_juice.txt"

JUICE_MAP = {
    "epl": Path("config/soccer/epl/epl_1x2_juice.csv"),
    "la_liga": Path("config/soccer/la_liga/laliga_1x2_juice.csv"),
    "bundesliga": Path("config/soccer/bundesliga/bundesliga_1x2_juice.csv"),
    "ligue1": Path("config/soccer/ligue1/ligue1_1x2_juice.csv"),
    "serie_a": Path("config/soccer/serie_a/seriea_1x2_juice.csv"),
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def decimal_to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1:
        return ""
    if decimal_odds >= 2.0:
        return f"+{int(round((decimal_odds - 1) * 100))}"
    return f"-{int(round(100 / (decimal_odds - 1)))}"


def find_band(prob, juice_df):
    match = juice_df[
        (juice_df["band_min"] <= prob) &
        (prob < juice_df["band_max"])
    ]
    if match.empty:
        raise ValueError(f"No juice band found for probability {prob}")
    return match.iloc[0]


def process_side(df, side, juice_tables, summary):
    prob_col = f"{side}_prob"

    df[f"{side}_fair_decimal"] = ""
    df[f"{side}_juice_band"] = ""
    df[f"{side}_extra_juice"] = ""
    df[f"{side}_adjusted_prob"] = ""
    df[f"{side}_adjusted_decimal"] = ""
    df[f"{side}_adjusted_american"] = ""

    for idx, row in df.iterrows():
        prob = row[prob_col]

        if pd.isna(prob) or prob <= 0 or prob >= 1:
            summary["rows_skipped"] += 1
            continue

        league = row["league"]
        juice_df = juice_tables[league]

        # Fair decimal
        fair_decimal = 1 / prob

        # Find band
        band_row = find_band(prob, juice_df)
        extra_juice = band_row["extra_juice"]
        band_label = f"{band_row['band_min']}-{band_row['band_max']}"

        # Apply juice
        adjusted_prob = prob + extra_juice
        if adjusted_prob >= 0.999:
            adjusted_prob = 0.999

        adjusted_decimal = 1 / adjusted_prob
        adjusted_american = decimal_to_american(adjusted_decimal)

        df.at[idx, f"{side}_fair_decimal"] = fair_decimal
        df.at[idx, f"{side}_juice_band"] = band_label
        df.at[idx, f"{side}_extra_juice"] = extra_juice
        df.at[idx, f"{side}_adjusted_prob"] = adjusted_prob
        df.at[idx, f"{side}_adjusted_decimal"] = adjusted_decimal
        df.at[idx, f"{side}_adjusted_american"] = adjusted_american

        summary["rows_processed"] += 1

    return df


# =========================
# CORE
# =========================

def main():

    with open(ERROR_LOG, "w") as log:

        log.write("=== APPLY JUICE RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:
            input_files = glob.glob(str(INPUT_DIR / "soccer_*.csv"))

            if not input_files:
                log.write("No input files found.\n")
                return

            summary = {
                "files_processed": 0,
                "rows_processed": 0,
                "rows_skipped": 0
            }

            for file_path in input_files:
                input_path = Path(file_path)
                df = pd.read_csv(input_path)

                if "league" not in df.columns:
                    raise ValueError("Input file missing 'league' column")

                leagues = df["league"].unique()
                juice_tables = {}

                for league in leagues:
                    if league not in JUICE_MAP:
                        raise ValueError(f"No juice config mapped for league: {league}")
                    juice_tables[league] = pd.read_csv(JUICE_MAP[league])

                for side in ["home", "draw", "away"]:
                    if f"{side}_prob" not in df.columns:
                        raise ValueError(f"Missing column: {side}_prob")
                    df = process_side(df, side, juice_tables, summary)

                output_path = OUTPUT_DIR / input_path.name
                df.to_csv(output_path, index=False)

                log.write(f"Wrote {output_path}\n")
                summary["files_processed"] += 1

            log.write("\n=== SUMMARY ===\n")
            log.write(f"Files processed: {summary['files_processed']}\n")
            log.write(f"Rows processed: {summary['rows_processed']}\n")
            log.write(f"Rows skipped: {summary['rows_skipped']}\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()
