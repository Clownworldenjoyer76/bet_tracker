#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

INPUT_DIR = Path("testing")
OUTPUT_DIR = INPUT_DIR / "csvs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def convert_xlsx_to_csv():
    xlsx_files = list(INPUT_DIR.glob("*.xlsx"))

    if not xlsx_files:
        print("No .xlsx files found in testing/")
        return

    for xlsx_path in xlsx_files:
        try:
            df = pd.read_excel(xlsx_path, engine="openpyxl")
            output_path = OUTPUT_DIR / f"{xlsx_path.stem}.csv"
            df.to_csv(output_path, index=False)
            print(f"Converted: {xlsx_path.name} -> {output_path}")
        except Exception as e:
            print(f"FAILED converting {xlsx_path.name}: {e}")


if __name__ == "__main__":
    convert_xlsx_to_csv()
