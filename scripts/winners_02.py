#!/usr/bin/env python3

import pandas as pd
import glob
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/winners/step_01")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/winner/step_02")

ERROR_DIR = Path("docs/win/errors/09_winners")
ERROR_LOG = ERROR_DIR / "winners_02.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1:
        return ""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    return int(-100 / (decimal_odds - 1))

def load_normalized_times():
    """
    Load all normalized files and build:
    game_id -> time
    """
    mapping = {}

    norm_files = glob.glob(str(NORMALIZED_DIR / "*.csv"))

    for file_path in norm_files:
        try:
            df = pd.read_csv(file_path)
            if "game_id" in df.columns and "time" in df.columns:
                for _, row in df.iterrows():
                    mapping[row["game_id"]] = row["time"]
        except Exception:
            continue

    return mapping

# =========================
# MAIN
# =========================

def process_files():

    summary_lines = []
    summary_lines.append(f"=== WINNERS_02 RUN @ {datetime.utcnow().isoformat()}Z ===")

    normalized_time_map = load_normalized_times()

    input_files = glob.glob(str(INPUT_DIR / "winners_*.csv"))

    files_processed = 0
    rows_processed = 0
    times_updated = 0

    for file_path in input_files:
        try:
            df = pd.read_csv(file_path)

            if "game_id" not in df.columns:
                continue

            # =========================
            # 1. UPDATE TIME
            # =========================

            if "time" in df.columns:
                for idx, row in df.iterrows():
                    gid = row["game_id"]
                    if gid in normalized_time_map:
                        new_time = normalized_time_map[gid]
                        if row["time"] != new_time:
                            df.at[idx, "time"] = new_time
                            times_updated += 1

            # =========================
            # 2. CREATE EDGE COLUMNS
            # =========================

            df["home_ml_edge"] = ""
            df["away_ml_edge"] = ""

            if all(col in df.columns for col in [
                "deci_dk_home_odds",
                "deci_home_ml_juice_odds_edge"
            ]):
                df["home_ml_edge"] = (
                    df["deci_dk_home_odds"] -
                    df["deci_home_ml_juice_odds_edge"]
                )

            if all(col in df.columns for col in [
                "deci_dk_away_odds",
                "deci_away_ml_juice_odds"
            ]):
                df["away_ml_edge"] = (
                    df["deci_dk_away_odds"] -
                    df["deci_away_ml_juice_odds"]
                )

            # =========================
            # 3. CREATE AMERICAN ODDS
            # =========================

            df["away_odds"] = ""
            df["home_odds"] = ""

            if "deci_dk_away_odds" in df.columns:
                df["away_odds"] = df["deci_dk_away_odds"].apply(to_american)

            if "deci_dk_home_odds" in df.columns:
                df["home_odds"] = df["deci_dk_home_odds"].apply(to_american)

            # =========================
            # 4. OUTPUT
            # =========================

            output_path = OUTPUT_DIR / Path(file_path).name
            df.to_csv(output_path, index=False)

            files_processed += 1
            rows_processed += len(df)

        except Exception as e:
            summary_lines.append(f"ERROR processing {file_path}")
            summary_lines.append(traceback.format_exc())

    summary_lines.append(f"Files processed: {files_processed}")
    summary_lines.append(f"Rows processed: {rows_processed}")
    summary_lines.append(f"Times updated: {times_updated}")

    with open(ERROR_LOG, "w") as f:
        f.write("\n".join(summary_lines))


if __name__ == "__main__":
    process_files()
