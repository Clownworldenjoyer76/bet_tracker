# scripts/soccer_calibration_curve.py

#!/usr/bin/env python3

import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# PATHS
# =========================

INPUT_FILE = Path("bets/soccer/calibration/soccer_calibration_master.csv")
OUTPUT_DIR = Path("bets/soccer/calibration")
OUTPUT_FILE = OUTPUT_DIR / "soccer_calibration_curve.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONFIG
# =========================

BUCKET_WIDTH = 0.02  # 2% probability buckets

# =========================
# MAIN
# =========================

def main():

    if not INPUT_FILE.exists():
        print("Master calibration file not found.")
        return

    df = pd.read_csv(INPUT_FILE)

    required_cols = ["implied_prob_fair", "decimal_odds", "result"]
    if not all(col in df.columns for col in required_cols):
        print("Missing required columns.")
        return

    # Drop invalid rows
    df = df.dropna(subset=required_cols)
    df = df[(df["implied_prob_fair"] > 0) & (df["implied_prob_fair"] < 1)]

    # =========================
    # BUILD BUCKETS (vectorized)
    # =========================

    df["bucket"] = (
        np.floor(df["implied_prob_fair"] / BUCKET_WIDTH) * BUCKET_WIDTH
    ).round(2)

    # =========================
    # AGGREGATION
    # =========================

    grouped = df.groupby("bucket").agg(
        n=("result", "count"),
        avg_implied_prob=("implied_prob_fair", "mean"),
        actual_win_rate=("result", "mean"),
        avg_decimal_odds=("decimal_odds", "mean")
    ).reset_index()

    # ROI calculation
    grouped["roi"] = (
        grouped["actual_win_rate"] * grouped["avg_decimal_odds"] - 1
    )

    # Calibration error
    grouped["prob_delta"] = (
        grouped["avg_implied_prob"] - grouped["actual_win_rate"]
    )

    # Required adjusted probability (historical realized)
    grouped["adjusted_probability"] = grouped["actual_win_rate"]

    # Personally acceptable decimal odds (safe division)
    grouped["acceptable_decimal_odds"] = np.where(
        grouped["adjusted_probability"] > 0,
        1 / grouped["adjusted_probability"],
        np.nan
    )

    # Sort
    grouped = grouped.sort_values("bucket")

    # Write output
    grouped.to_csv(OUTPUT_FILE, index=False)

    print(f"Wrote calibration curve to {OUTPUT_FILE}")
    print(f"Total buckets: {len(grouped)}")


if __name__ == "__main__":
    main()
