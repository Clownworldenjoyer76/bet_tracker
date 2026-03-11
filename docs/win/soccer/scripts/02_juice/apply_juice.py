#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import traceback
import sys
from datetime import datetime

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/soccer/01_merge")
OUTPUT_DIR = Path("docs/win/soccer/02_juice")

ERROR_DIR = Path("docs/win/soccer/errors/02_juice")
ERROR_LOG = ERROR_DIR / "01_apply_juice.txt"

JUICE_MAP = {
    "epl": Path("config/soccer/epl/3way_juice.csv"),
    "laliga": Path("config/soccer/la_liga/3way_juice.csv"),
    "bundesliga": Path("config/soccer/bundesliga/3way_juice.csv"),
    "ligue1": Path("config/soccer/ligue1/3way_juice.csv"),
    "seriea": Path("config/soccer/serie_a/3way_juice.csv"),
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


def find_closest_juice(prob, juice_df, side):
    side_df = juice_df[juice_df["side"] == side]
    
    if side_df.empty:
        raise ValueError(f"No juice data found for side {side}")

    # Find the row with the fair_prob closest to our actual prob
    closest_idx = (side_df["fair_prob"] - prob).abs().idxmin()
    return side_df.loc[closest_idx]


def get_prob_col_name(df, side):
    if f"{side}_win_prob" in df.columns:
        return f"{side}_win_prob"
    if f"{side}_prob" in df.columns:
        return f"{side}_prob"
    raise ValueError(f"Missing probability column for {side}")


def process_side(df, side, juice_tables, summary):

    prob_col = get_prob_col_name(df, side)

    df[f"{side}_fair_decimal"] = pd.NA
    df[f"{side}_adjusted_prob"] = pd.NA
    df[f"{side}_adjusted_decimal"] = pd.NA

    df[f"{side}_matched_fair_prob"] = pd.NA
    df[f"{side}_extra_juice"] = pd.NA
    df[f"{side}_adjusted_american"] = ""

    for idx, row in df.iterrows():

        prob = row[prob_col]

        if pd.isna(prob) or prob <= 0 or prob >= 1:
            summary["rows_skipped"] += 1
            continue

        market = row["market"]

        if market not in juice_tables:
            raise ValueError(f"No juice config mapped for market: {market}")

        juice_df = juice_tables[market]

        fair_decimal = 1 / prob

        matched_row = find_closest_juice(prob, juice_df, side)

        extra_juice = matched_row["extra_juice"]
        matched_fair_prob = matched_row["fair_prob"]

        adjusted_prob = prob + extra_juice

        if adjusted_prob >= 0.999:
            adjusted_prob = 0.999

        adjusted_decimal = 1 / adjusted_prob
        adjusted_american = decimal_to_american(adjusted_decimal)

        df.at[idx, f"{side}_fair_decimal"] = float(fair_decimal)
        df.at[idx, f"{side}_matched_fair_prob"] = float(matched_fair_prob)
        df.at[idx, f"{side}_extra_juice"] = float(extra_juice)
        df.at[idx, f"{side}_adjusted_prob"] = float(adjusted_prob)
        df.at[idx, f"{side}_adjusted_decimal"] = float(adjusted_decimal)
        df.at[idx, f"{side}_adjusted_american"] = adjusted_american

        summary["rows_processed"] += 1

    return df


# =========================
# CORE
# =========================

def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as log:
        log.write("=== APPLY JUICE RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

    try:

        # recursive=True ensures we catch files inside subfolders like /market_model/
        input_files = glob.glob(str(INPUT_DIR / "**" / "soccer_*.csv"), recursive=True)

        if not input_files:
            with open(ERROR_LOG, "a", encoding="utf-8") as log:
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

            if "market" not in df.columns:
                raise ValueError(f"Missing 'market' column in {input_path.name}")

            unique_markets = df["market"].unique()

            juice_tables = {}

            for m in unique_markets:

                if m not in JUICE_MAP:
                    raise ValueError(f"No juice config mapped for market: {m}")

                config_path = JUICE_MAP[m]

                if not config_path.exists():
                    raise FileNotFoundError(f"Missing juice config: {config_path}")

                juice_tables[m] = pd.read_csv(config_path)

            for side in ["home", "draw", "away"]:
                df = process_side(df, side, juice_tables, summary)

            # Keep folder structure flat in output, or use input_path.name
            output_path = OUTPUT_DIR / input_path.name

            df.to_csv(output_path, index=False)

            with open(ERROR_LOG, "a", encoding="utf-8") as log:
                log.write(f"Wrote {output_path}\n")

            summary["files_processed"] += 1

        with open(ERROR_LOG, "a", encoding="utf-8") as log:
            log.write("\n=== SUMMARY ===\n")
            log.write(f"Files processed: {summary['files_processed']}\n")
            log.write(f"Rows processed: {summary['rows_processed']}\n")
            log.write(f"Rows skipped: {summary['rows_skipped']}\n")

    except Exception as e:

        with open(ERROR_LOG, "a", encoding="utf-8") as log:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())

        sys.exit(1)


if __name__ == "__main__":
    main()
