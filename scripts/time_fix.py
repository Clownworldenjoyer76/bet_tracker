#!/usr/bin/env python3

import csv
from pathlib import Path

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/first")

# =========================
# HELPERS
# =========================

def extract_year_from_filename(path: Path) -> str:
    """
    Expected filename pattern:
    dk_{league}_{market}_YYYY_MM_DD.csv
    """
    parts = path.stem.split("_")
    if len(parts) < 4:
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    return parts[-3]  # YYYY

def normalize_date(md: str, year: str) -> str:
    """
    Converts M/D -> YYYY_MM_DD
    """
    month, day = md.split("/")
    return f"{year}_{month.zfill(2)}_{day.zfill(2)}"

# =========================
# MAIN
# =========================

def main():
    for path in INPUT_DIR.glob("*.csv"):
        year = extract_year_from_filename(path)

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames or []

        if "date" not in fieldnames:
            continue

        for row in rows:
            raw_date = row.get("date")
            if raw_date:
                row["date"] = normalize_date(raw_date, year)

        # overwrite file in place
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

if __name__ == "__main__":
    main()
