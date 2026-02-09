#!/usr/bin/env python3

import csv
from pathlib import Path
import re

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/first")
ERROR_DIR = Path("docs/win/errors")
ERROR_LOG = ERROR_DIR / "time_fix.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

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
    if len(parts) < 4 or not parts[-3].isdigit():
        raise ValueError(f"Cannot extract year from filename: {path.name}")
    return parts[-3]

def normalize_date(md: str, year: str):
    """
    Converts M/D or MM/DD -> YYYY_MM_DD
    Returns (normalized_value, was_updated, was_unrecognized)
    """
    if md is None:
        return md, False, False

    s = str(md).strip()

    if YMD_RE.match(s):
        return s, False, False

    m = MD_RE.match(s)
    if not m:
        return s, False, True

    month, day = m.groups()
    return f"{year}_{month.zfill(2)}_{day.zfill(2)}", True, False

# =========================
# MAIN
# =========================

def main():
    files_processed = 0
    files_skipped = 0
    filename_errors = 0

    rows_seen = 0
    rows_updated = 0
    rows_unrecognized = 0

    for path in INPUT_DIR.glob("*.csv"):
        try:
            year = extract_year_from_filename(path)
        except Exception as e:
            filename_errors += 1
            with open(ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(f"FILENAME ERROR: {path.name}\n{e}\n\n")
            continue

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames or []

        if "date" not in fieldnames:
            files_skipped += 1
            with open(ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(f"SKIPPED FILE (missing date column): {path.name}\n")
            continue

        files_processed += 1

        for row in rows:
            raw_date = row.get("date")
            if raw_date is None:
                continue

            rows_seen += 1
            new_date, updated, unrecognized = normalize_date(raw_date, year)

            if updated:
                row["date"] = new_date
                rows_updated += 1
            elif unrecognized:
                rows_unrecognized += 1

        # overwrite file in place
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # =========================
    # FAILURE THRESHOLDS
    # =========================

    if filename_errors > 0:
        raise RuntimeError("time_fix aborted: filename parse failures detected")

    if rows_seen > 0:
        unrecognized_ratio = rows_unrecognized / rows_seen
        if unrecognized_ratio > 0.25:
            raise RuntimeError(
                f"time_fix aborted: {unrecognized_ratio:.1%} unrecognized date formats"
            )

    # =========================
    # SUMMARY LOG
    # =========================

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write("\nTIME FIX SUMMARY\n")
        f.write("================\n")
        f.write(f"Files processed: {files_processed}\n")
        f.write(f"Files skipped (no date column): {files_skipped}\n")
        f.write(f"Filename errors: {filename_errors}\n\n")
        f.write(f"Rows with dates: {rows_seen}\n")
        f.write(f"Rows normalized: {rows_updated}\n")
        f.write(f"Rows unrecognized: {rows_unrecognized}\n")

        if rows_updated == 0:
            f.write(
                "\nWARNING: zero dates normalized "
                "(all dates already normalized)\n"
            )

if __name__ == "__main__":
    main()
