#!/usr/bin/env python3

import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# PATHS
# =========================

MASTER_FILE = Path("bets/soccer/calibration/soccer_calibration_master.csv")
OUTPUT_DIR = Path("config/soccer")
OUTPUT_FILE = OUTPUT_DIR / "epl_1x2_juice.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONFIG
# =========================

BUCKET_WIDTH = 0.05
MIN_SAMPLE = 150

# =========================
# MAIN
# =========================

def main():

    if not MASTER_FILE.exists():
        print("Calibration master file not found.")
        return

    df = pd.read_csv(MASTER_FILE)

    required = ["implied_prob_fair", "result", "market"]
    if not all(c in df.columns for c in required):
        print("Missing required columns.")
        return

    df = df.dropna(subset=required)
    df = df[(df["implied_prob_fair"] > 0) & (df["implied_prob_fair"] < 1)]

    # Build probability buckets
    df["band_min"] = (df["implied_prob_fair"] / BUCKET_WIDTH).apply(np.floor) * BUCKET_WIDTH
    df["band_min"] = df["band_min"].round(2)
    df["band_max"] = (df["band_min"] + BUCKET_WIDTH).round(2)

    juice_rows = []

    for market in ["1x2_home", "1x2_draw", "1x2_away"]:

        sub = df[df["market"] == market]

        grouped = sub.groupby(["band_min", "band_max"]).agg(
            n=("result", "count"),
            avg_prob=("implied_prob_fair", "mean"),
            actual_win_rate=("result", "mean")
        ).reset_index()

        # Filter low-sample bands
        grouped = grouped[grouped["n"] >= MIN_SAMPLE]

        if grouped.empty:
            continue

        # Compute delta
        grouped["extra_juice"] = grouped["avg_prob"] - grouped["actual_win_rate"]

        for _, row in grouped.iterrows():
            band_label = f"{row['band_min']:.2f} to {row['band_max']:.2f}"

            juice_rows.append({
                "band": band_label,
                "band_min": row["band_min"],
                "band_max": row["band_max"],
                "side": market.replace("1x2_", ""),
                "extra_juice": row["extra_juice"]
            })

    juice_df = pd.DataFrame(juice_rows)

    if juice_df.empty:
        print("No valid bands generated.")
        return

    juice_df = juice_df.sort_values(["side", "band_min"])
    juice_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Wrote {OUTPUT_FILE} ({len(juice_df)} bands)")


if __name__ == "__main__":
    main()
