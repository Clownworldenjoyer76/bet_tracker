#!/usr/bin/env python3

import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# PATHS
# =========================

INPUT_FILE = Path("bets/soccer/calibration/soccer_calibration_master.csv")
OUTPUT_DIR = Path("bets/soccer/calibration")
OUTPUT_FILE = OUTPUT_DIR / "soccer_calibration_curve_bundesliga.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONFIG
# =========================

LEAGUE_FILTER = "BUNDESLIGA"
BUCKET_WIDTH = 0.02  # 2% probability buckets

# =========================
# MAIN
# =========================

def main():

    if not INPUT_FILE.exists():
        print("Master calibration file not found.")
        return

    df = pd.read_csv(INPUT_FILE)

    df = df[df["league"] == LEAGUE_FILTER].copy()

    required_cols = ["implied_prob_fair", "decimal_odds", "result"]
    if not all(col in df.columns for col in required_cols):
        print("Missing required columns.")
        return

    df = df.dropna(subset=required_cols)
    df = df[(df["implied_prob_fair"] > 0) & (df["implied_prob_fair"] < 1)]

    if df.empty:
        print("No rows after league filtering.")
        return

    df["bucket"] = (
        np.floor(df["implied_prob_fair"] / BUCKET_WIDTH) * BUCKET_WIDTH
    ).round(2)

    grouped = df.groupby("bucket").agg(
        n=("result", "count"),
        avg_implied_prob=("implied_prob_fair", "mean"),
        actual_win_rate=("result", "mean"),
        avg_decimal_odds=("decimal_odds", "mean")
    ).reset_index()

    grouped["roi"] = (
        grouped["actual_win_rate"] * grouped["avg_decimal_odds"] - 1
    )

    grouped["prob_delta"] = (
        grouped["avg_implied_prob"] - grouped["actual_win_rate"]
    )

    grouped["adjusted_probability"] = grouped["actual_win_rate"]

    grouped["acceptable_decimal_odds"] = np.where(
        grouped["adjusted_probability"] > 0,
        1 / grouped["adjusted_probability"],
        np.nan
    )

    grouped = grouped.sort_values("bucket")

    grouped.to_csv(OUTPUT_FILE, index=False)

    print(f"Wrote calibration curve to {OUTPUT_FILE}")
    print(f"Total buckets: {len(grouped)}")


if __name__ == "__main__":
    main()
