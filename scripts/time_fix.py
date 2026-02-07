#!/usr/bin/env python3

import csv
from pathlib import Path
import re

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/first")

# =========================
# HELPERS
# =========================

MD_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})\s*$")
YMD_RE = re.compile(r"^\d{4}_\d{2}_\d{2}$")

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
    Converts M/D or MM/DD -> YYYY_MM_DD
    Leaves everything else unchanged
    """
    if md is None:
        return md

    s = str(md).strip()

    # already normalized
    if YMD_RE.match(s):
        return s

    m = MD_RE.match(s)
    if not m:
        return s

    month, day = m.groups()
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
