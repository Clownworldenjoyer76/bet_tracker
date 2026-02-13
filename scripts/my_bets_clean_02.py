#!/usr/bin/env python3

import pandas as pd
import glob
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/my_bets/step_01")
OUTPUT_DIR = Path("docs/win/my_bets/step_02")

ERROR_DIR = Path("docs/win/errors/01_raw")
ERROR_LOG = ERROR_DIR / "my_bets_clean_02.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONSTANTS
# =========================

COLUMNS_TO_DELETE = [
    "juice_bet_id",
    "sportsbook",
    "number_of_legs",
    "bet_leg_id",
    "long_description_of_leg",
    "event_start_date",
    "event_name",
]

LEAGUE_PREFIX_MAP = {
    "NBA": "nba_",
    "CBB": "ncaab_",
}

LEG_TYPE_SUFFIX_MAP = {
    "Moneyline": "moneyline",
    "GameOu": "totals",
    "Spread": "spreads",
}

# =========================
# HELPERS
# =========================

def build_league_value(leg_league, leg_type):
    prefix = LEAGUE_PREFIX_MAP.get(str(leg_league).strip(), "")
    suffix = LEG_TYPE_SUFFIX_MAP.get(str(leg_type).strip(), "")

    if prefix and suffix:
        return f"{prefix}{suffix}"
    return ""

# =========================
# MAIN
# =========================

def process_files():

    summary = []
    summary.append(f"=== MY_BETS_CLEAN_02 RUN @ {datetime.utcnow().isoformat()}Z ===")

    input_files = glob.glob(str(INPUT_DIR / "*.csv"))

    files_processed = 0
    rows_processed = 0

    for file_path in input_files:
        try:
            df = pd.read_csv(file_path)

            # =========================
            # DELETE COLUMNS
            # =========================
            for col in COLUMNS_TO_DELETE:
                if col in df.columns:
                    df = df.drop(columns=[col])

            # =========================
            # CREATE LEAGUE COLUMN
            # =========================
            if "leg_league" in df.columns and "leg_type" in df.columns:
                df["league"] = df.apply(
                    lambda row: build_league_value(
                        row["leg_league"],
                        row["leg_type"]
                    ),
                    axis=1
                )
            else:
                df["league"] = ""

            # =========================
            # OUTPUT
            # =========================
            output_path = OUTPUT_DIR / Path(file_path).name
            df.to_csv(output_path, index=False)

            files_processed += 1
            rows_processed += len(df)

        except Exception:
            summary.append(f"ERROR processing {file_path}")
            summary.append(traceback.format_exc())

    summary.append(f"Files processed: {files_processed}")
    summary.append(f"Rows processed: {rows_processed}")

    with open(ERROR_LOG, "w") as f:
        f.write("\n".join(summary))


if __name__ == "__main__":
    process_files()
