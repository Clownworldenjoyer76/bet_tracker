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

    # Add or overwrite win_probability
    df["win_probability"] = df["odds"].apply(implied_win_probability)

    # Create ~3% probability buckets
    step = 0.03
    bins = [round(i * step, 4) for i in range(int(1 / step) + 1)]
    if bins[-1] < 1.0:
        bins.append(1.0)

    labels = [
        f"{int(bins[i] * 100)}–{int(bins[i + 1] * 100)}%"
        for i in range(len(bins) - 1)
    ]

    df["probability_bucket"] = pd.cut(
        df["win_probability"],
        bins=bins,
        labels=labels,
        include_lowest=True,
        right=False
    )

    df.to_csv(path, index=False)


def main():
    if not os.path.isdir(CSV_DIR):
        raise FileNotFoundError(f"Directory not found: {CSV_DIR}")

    for filename in os.listdir(CSV_DIR):
        if filename.lower().endswith(".csv"):
            process_csv(os.path.join(CSV_DIR, filename))


if __name__ == "__main__":
    main()
