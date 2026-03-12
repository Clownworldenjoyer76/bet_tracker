# scripts/merge_scripts/merge_folder_files_03_basketball_edges.py

import os
import pandas as pd

# =========================================================
# ==================== CONFIG SECTION =====================
# =========================================================

INPUT_FOLDER = "docs/win/basketball/03_edges"
OUTPUT_FOLDER = "docs/win/basketball/03_edges/merged"

LEAGUES = ["NBA", "NCAAB"]
MARKETS = ["moneyline", "spread", "total"]

FILE_EXTENSION = ".csv"

# =========================================================


os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def get_files():
    files = []

    for name in os.listdir(INPUT_FOLDER):

        if not name.endswith(FILE_EXTENSION):
            continue

        files.append(name)

    return files


def main():

    files = get_files()

    if not files:
        print("No files found.")
        return

    for league in LEAGUES:
        for market in MARKETS:

            matching_files = []

            for f in files:

                if league in f and market in f:
                    matching_files.append(f)

            if not matching_files:
                continue

            print(f"Merging {league} {market} ({len(matching_files)} files)")

            dfs = []

            for file in sorted(matching_files):

                path = os.path.join(INPUT_FOLDER, file)

                try:
                    df = pd.read_csv(path)
                    dfs.append(df)

                except Exception as e:
                    print(f"Skipping {file}: {e}")

            if not dfs:
                continue

            merged = pd.concat(dfs, ignore_index=True)

            output_file = f"edges_{league}_{market}.csv"
            output_path = os.path.join(OUTPUT_FOLDER, output_file)

            merged.to_csv(output_path, index=False)

            print(f"Created: {output_path}")


if __name__ == "__main__":

    main()
