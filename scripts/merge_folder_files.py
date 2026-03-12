import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# =========================================================
# =============== MATS CONFIGURATION SECTION ===============
# =========================================================


INPUT_FOLDER = r"docs/win/basketball/00_intake/sportsbook"
# Folder containing the files you want to merge.

LEAGUE_FILTER = "NBA"
# Example: "NBA", "NCAAB", etc.
# To scan the ENTIRE folder and merge everything use:
# 
# LEAGUE_FILTER = ""

OUTPUT_FILE = f"docs/win/basketball/00_intake/sportsbook/merged/sportsbook_{LEAGUE_FILTER}_merged.csv"
# Output file location.

FILE_EXTENSION = ".csv"
# File type to merge

ADD_SOURCE_COLUMN = True
# True = adds column showing which file each row came from
# False = no extra column

# =========================================================


# ---------------- Logger ---------------- #

LOG_DIR = "scripts/errors_log"
LOG_FILE = os.path.join(LOG_DIR, "merge_log.txt")

# ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


def get_files(folder, extension):
    files = []

    for root, _, filenames in os.walk(folder):

        for name in filenames:

            if not name.lower().endswith(extension):
                continue

            # Apply league filter if one is set
            if LEAGUE_FILTER and LEAGUE_FILTER not in name:
                continue

            files.append(os.path.join(root, name))

    return files


def detect_all_columns(files):
    """
    Scan files once to determine all possible columns.
    """

    column_set = set()

    for file in files:

        try:
            df = pd.read_csv(file, nrows=5)
            column_set.update(df.columns)

        except Exception as e:
            log(f"Column detection failed for {file}: {e}")

    return sorted(list(column_set))


def merge_files(files, all_columns):

    first_write = True

    for file in files:

        log(f"Processing {file}")

        try:

            df = pd.read_csv(file)

            if ADD_SOURCE_COLUMN:
                df["source_file"] = Path(file).name

            # align schema
            for col in all_columns:
                if col not in df.columns:
                    df[col] = None

            df = df[all_columns + (["source_file"] if ADD_SOURCE_COLUMN else [])]

            if first_write:
                df.to_csv(OUTPUT_FILE, index=False, mode="w")
                first_write = False
            else:
                df.to_csv(OUTPUT_FILE, index=False, header=False, mode="a")

        except Exception as e:
            log(f"FAILED reading {file}: {e}")


def main():

    log("Starting merge process")

    files = get_files(INPUT_FOLDER, FILE_EXTENSION)

    if not files:
        log("No files found")
        return

    log(f"{len(files)} files detected")

    all_columns = detect_all_columns(files)

    log(f"{len(all_columns)} unique columns detected")

    merge_files(files, all_columns)

    log("Merge complete")


if __name__ == "__main__":
    main()
