#!/usr/bin/env python3

import os
import pandas as pd

CSV_DIR = "testing/csvs"


def implied_win_probability(odds):
    try:
        odds = float(odds)
        if odds <= 0:
            return None
        return 1.0 / odds
    except (ValueError, TypeError):
        return None


def process_csv(path):
    df = pd.read_csv(path)

    # Add or overwrite win_probability column
    df["win_probability"] = df["odds"].apply(implied_win_probability)

    df.to_csv(path, index=False)


def main():
    if not os.path.isdir(CSV_DIR):
        raise FileNotFoundError(f"Directory not found: {CSV_DIR}")

    for filename in os.listdir(CSV_DIR):
        if filename.lower().endswith(".csv"):
            full_path = os.path.join(CSV_DIR, filename)
            process_csv(full_path)


if __name__ == "__main__":
    main()
