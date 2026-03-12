import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# ---------------- SETTINGS ---------------- #

INPUT_FOLDER = r"C:\path\to\folderX"
OUTPUT_FILE = r"C:\path\to\combined_output.csv"

FILE_EXTENSION = ".csv"
CHUNK_SIZE = 200000        # rows per chunk for large files
ADD_SOURCE_COLUMN = True

# ---------------- Logger ---------------- #

LOG_DIR = "scripts/errors_log"
LOG_FILE = os.path.join(LOG_DIR, "merge_log.txt")

# ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# ------------------------------------------ #


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
            if name.lower().endswith(extension):
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

            for chunk in pd.read_csv(file, chunksize=CHUNK_SIZE):

                if ADD_SOURCE_COLUMN:
                    chunk["source_file"] = Path(file).name

                # align schema
                for col in all_columns:
                    if col not in chunk.columns:
                        chunk[col] = None

                chunk = chunk[all_columns + (["source_file"] if ADD_SOURCE_COLUMN else [])]

                if first_write:
                    chunk.to_csv(OUTPUT_FILE, index=False, mode="w")
                    first_write = False
                else:
                    chunk.to_csv(OUTPUT_FILE, index=False, header=False, mode="a")

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
