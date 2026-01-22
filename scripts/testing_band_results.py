#!/usr/bin/env python3

import os
import pandas as pd

INPUT_DIR = "testing/csvs"
OUTPUT_DIR = "testing/csvs/bands"


def process_csv(path, output_path):
    df = pd.read_csv(path)

    # Normalize status just in case
    df["status"] = df["status"].str.strip()

    # Aggregate wins and losses by probability bucket
    grouped = (
        df.groupby("probability_bucket")["status"]
        .value_counts()
        .unstack(fill_value=0)
        .rename(columns={"Win": "wins", "Loss": "losses"})
    )

    # Ensure both columns exist
    if "wins" not in grouped.columns:
        grouped["wins"] = 0
    if "losses" not in grouped.columns:
        grouped["losses"] = 0

    grouped["total_bets"] = grouped["wins"] + grouped["losses"]

    grouped.reset_index().to_csv(output_path, index=False)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in os.listdir(INPUT_DIR):
        if not filename.lower().endswith(".csv"):
            continue

        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        process_csv(input_path, output_path)


if __name__ == "__main__":
    main()
