#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

# =========================
# PATHS
# =========================

INPUT_FILE = Path("bets/historic/NCAA MENS BASKETBALL/spread_history_since2003.csv")
OUTPUT_FILE = Path("bets/historic/NCAA MENS BASKETBALL/ncaab_spreads_juice.csv")

# =========================
# SETTINGS
# =========================

MIN_GAMES = 50     # below this → juice = 0
K = 200            # Bayesian shrink strength


# =========================
# MAIN
# =========================

def main():

    df = pd.read_csv(INPUT_FILE)

    required_cols = [
        "closing_spread",
        "game_count",
        "cover_pct"
    ]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    def compute_juice(row):

        spread = float(row["closing_spread"])
        n = int(row["game_count"])
        cover_pct = float(row["cover_pct"])

        if n < MIN_GAMES:
            return 0.0

        # Bayesian shrink toward 0.50
        p_adj = ((cover_pct * n) + (0.5 * K)) / (n + K)

        return round(p_adj - 0.5, 6)

    df["extra_juice"] = df.apply(compute_juice, axis=1)

    output = df[["closing_spread", "extra_juice"]].copy()
    output.columns = ["spread", "extra_juice"]

    output = output.sort_values("spread").reset_index(drop=True)

    output.to_csv(OUTPUT_FILE, index=False)

    print(f"Created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
