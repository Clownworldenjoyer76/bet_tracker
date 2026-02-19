#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/winners/step_02_1")
OUTPUT_DIR = Path("docs/win/winners/step_03")
ERROR_LOG = Path("docs/win/errors/winners_04.txt")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

# =========================
# CONFIG
# =========================

EDGE_COLUMNS = [
    "home_ml_edge",
    "away_ml_edge",
    "home_spread_edge",
    "away_spread_edge",
    "over_edge",
    "under_edge",
]

EDGE_THRESHOLD = 0.1

# =========================
# HELPERS
# =========================

def safe_float(series):
    return pd.to_numeric(series, errors="coerce")

# =========================
# CORE
# =========================

def process_files():
    files = glob.glob(str(INPUT_DIR / "*.csv"))

    for file_path in files:
        try:
            df = pd.read_csv(file_path)

            # Ensure edge columns exist
            for col in EDGE_COLUMNS:
                if col not in df.columns:
                    df[col] = 0

            # Convert to numeric safely
            for col in EDGE_COLUMNS:
                df[col] = safe_float(df[col])

            # Filter rows where ANY edge > threshold
            mask = (
                (df["home_ml_edge"] > EDGE_THRESHOLD) |
                (df["away_ml_edge"] > EDGE_THRESHOLD) |
                (df["home_spread_edge"] > EDGE_THRESHOLD) |
                (df["away_spread_edge"] > EDGE_THRESHOLD) |
                (df["over_edge"] > EDGE_THRESHOLD) |
                (df["under_edge"] > EDGE_THRESHOLD)
            )

            filtered_df = df[mask].copy()

            # Write output with same filename
            output_path = OUTPUT_DIR / Path(file_path).name
            filtered_df.to_csv(output_path, index=False)

            print(f"Wrote {output_path} | rows_out={len(filtered_df)}")

        except Exception as e:
            with open(ERROR_LOG, "w") as f:
                f.write("WINNERS_04 ERROR\n")
                f.write(traceback.format_exc())
            print(f"ERROR processing {file_path}")
            raise e


if __name__ == "__main__":
    process_files()
