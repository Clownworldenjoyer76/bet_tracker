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
ERROR_LOG = Path("docs/win/errors/step_03/winners_05.txt")

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

            # Ensure required columns exist
            for col in ["league", "bet", "total", "diff"]:
                if col not in df.columns:
                    df[col] = None

            # Convert numeric columns safely
            for col in EDGE_COLUMNS + ["total", "diff"]:
                df[col] = safe_float(df[col])

            # =========================
            # BASE EDGE FILTER (ALL ROWS)
            # =========================

            base_mask = (
                (df["home_ml_edge"] > EDGE_THRESHOLD) |
                (df["away_ml_edge"] > EDGE_THRESHOLD) |
                (df["home_spread_edge"] > EDGE_THRESHOLD) |
                (df["away_spread_edge"] > EDGE_THRESHOLD) |
                (df["over_edge"] > EDGE_THRESHOLD) |
                (df["under_edge"] > EDGE_THRESHOLD)
            )

            # =========================
            # CUSTOM NCAAB TOTALS OVER LOGIC
            # =========================

            is_ncaab_over = (
                (df["league"] == "ncaab_totals") &
                (df["bet"] == "over_bet")
            )

            under_150_mask = (
                (df["total"] < 150) &
                (df["over_edge"] >= 0.40) &
                (df["diff"] >= 4)
            )

            over_150_mask = (
                (df["total"] > 150) &
                (df["diff"] >= 2)
            )

            custom_mask = is_ncaab_over & (under_150_mask | over_150_mask)

            # =========================
            # FINAL MASK
            # =========================

            # For NCAAB totals over → must pass custom rule
            # For everything else → must pass base edge rule

            final_mask = (
                (is_ncaab_over & (under_150_mask | over_150_mask)) |
                (~is_ncaab_over & base_mask)
            )

            filtered_df = df[final_mask].copy()

            # Write output with same filename
            output_path = OUTPUT_DIR / Path(file_path).name
            filtered_df.to_csv(output_path, index=False)

            print(f"Wrote {output_path} | rows_out={len(filtered_df)}")

        except Exception as e:
            with open(ERROR_LOG, "w") as f:
                f.write("WINNERS_05 ERROR\n")
                f.write(traceback.format_exc())
            print(f"ERROR processing {file_path}")
            raise e


if __name__ == "__main__":
    process_files()
