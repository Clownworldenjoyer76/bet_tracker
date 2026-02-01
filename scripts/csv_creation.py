#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

# Existing paths (UNCHANGED)
INPUT_DIR = Path("testing")
OUTPUT_DIR = INPUT_DIR / "csvs"

# New additional paths
DUMP_INPUT_DIR = Path("docs/win/dump")
DUMP_OUTPUT_DIR = DUMP_INPUT_DIR / "csvs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DUMP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def convert_directory(input_dir: Path, output_dir: Path):
    xlsx_files = list(input_dir.glob("*.xlsx"))

    if not xlsx_files:
        print(f"No .xlsx files found in {input_dir}/")
        return

    for xlsx_path in xlsx_files:
        try:
            df = pd.read_excel(xlsx_path, engine="openpyxl")
            output_path = output_dir / f"{xlsx_path.stem}.csv"
            df.to_csv(output_path, index=False)
            print(f"Converted: {xlsx_path} -> {output_path}")
        except Exception as e:
            print(f"FAILED converting {xlsx_path.name}: {e}")


def convert_xlsx_to_csv():
    # Original behavior
    convert_directory(INPUT_DIR, OUTPUT_DIR)

    # New additional behavior
    convert_directory(DUMP_INPUT_DIR, DUMP_OUTPUT_DIR)


if __name__ == "__main__":
    convert_xlsx_to_csv()
