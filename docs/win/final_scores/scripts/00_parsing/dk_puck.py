#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

SPORTSBOOK_DIR = Path("docs/win/hockey/00_intake/sportsbook")
# UPDATED: Pointing to the new NHL-specific score directory
FINAL_DIR = Path("docs/win/final_scores/results/nhl/final_scores")
ERROR_DIR = Path("docs/win/final_scores/errors")
LOG_FILE = ERROR_DIR / "dk_puck_log.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOGGING
# =========================

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


log("========== DK PUCK SCRIPT START ==========")

try:
    sportsbook_files = sorted(SPORTSBOOK_DIR.glob("hockey_*.csv"))

    if not sportsbook_files:
        log("No sportsbook files found.")
    else:
        log(f"Found {len(sportsbook_files)} sportsbook files.")

    for sb_file in sportsbook_files:
        try:
            # Extract date from filename (e.g., hockey_2026_03_01.csv -> 2026_03_01)
            date_part = sb_file.stem.replace("hockey_", "")
            final_file = FINAL_DIR / f"{date_part}_final_scores_NHL.csv"

            log(f"Processing sportsbook file: {sb_file.name}")
            log(f"Looking for final file: {final_file.name}")

            if not final_file.exists():
                log(f"Final file {final_file.name} does NOT exist in {FINAL_DIR}. Skipping.")
                continue

            sportsbook_df = pd.read_csv(sb_file)
            final_df = pd.read_csv(final_file)

            log(f"Sportsbook rows: {len(sportsbook_df)}")
            log(f"Final rows: {len(final_df)}")

            # Validate required columns
            required_cols = ["game_date", "away_team", "home_team",
                             "away_puck_line", "home_puck_line", "total"]

            for col in required_cols:
                if col not in sportsbook_df.columns:
                    log(f"Missing column in sportsbook: {col}. Skipping file.")
                    raise ValueError(f"Missing sportsbook column {col}")

            merge_cols = ["game_date", "away_team", "home_team"]

            for col in merge_cols:
                if col not in final_df.columns:
                    log(f"Missing column in final file: {col}. Skipping file.")
                    raise ValueError(f"Missing final column {col}")

            # Rename DK columns to distinguish them from final results
            sportsbook_df = sportsbook_df.rename(columns={
                "away_puck_line": "dk_away_puck_line",
                "home_puck_line": "dk_home_puck_line",
                "total": "dk_total"
            })

            sportsbook_subset = sportsbook_df[
                merge_cols + [
                    "dk_away_puck_line",
                    "dk_home_puck_line",
                    "dk_total"
                ]
            ]

            # Left merge adds DK info to your existing score file
            merged_df = final_df.merge(
                sportsbook_subset,
                on=merge_cols,
                how="left"
            )

            # Log match diagnostics
            dk_nulls = merged_df["dk_total"].isna().sum()
            log(f"Rows with missing DK match: {dk_nulls}")

            # Overwrite the original score file with the new merged data
            merged_df.to_csv(final_file, index=False)

            log(f"Successfully updated {final_file.name}")

        except Exception as file_error:
            log(f"ERROR processing {sb_file.name}")
            log(traceback.format_exc())
            continue

except Exception as e:
    log("FATAL ERROR IN DK PUCK SCRIPT")
    log(traceback.format_exc())

log("========== DK PUCK SCRIPT END ==========\n")
