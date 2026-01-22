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

    # Define probability buckets
    bins = [
        0.0, 0.10, 0.20, 0.30, 0.40,
        0.50, 0.60, 0.70, 0.80, 0.90, 1.00
    ]

    labels = [
        "0–10%",
        "10–20%",
        "20–30%",
        "30–40%",
        "40–50%",
        "50–60%",
        "60–70%",
        "70–80%",
        "80–90%",
        "90–100%"
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
            full_path = os.path.join(CSV_DIR, filename)
            process_csv(full_path)


if __name__ == "__main__":
    main()
