#!/usr/bin/env python3

import pandas as pd
import glob
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/winners/step_02_1")
OUTPUT_DIR = Path("docs/win/winners/step_02_1")
CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
ERROR_LOG = Path("docs/win/errors/winners_04.txt")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def to_float(x):
    try:
        if pd.isna(x):
            return None
        s = str(x).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

def build_projection_map(log):
    """
    Build:
        { game_id : game_projected_points }
    From all cleaned/*.csv files.
    Skip files without game_projected_points column.
    """

    projection_map = {}

    files = sorted(glob.glob(str(CLEANED_DIR / "*.csv")))

    files_scanned = 0
    files_used = 0
    rows_loaded = 0
    files_skipped_no_column = 0

    for path in files:
        files_scanned += 1
        try:
            df = pd.read_csv(path)

            if "game_id" not in df.columns:
                continue

            if "game_projected_points" not in df.columns:
                files_skipped_no_column += 1
                continue

            files_used += 1

            for _, row in df.iterrows():
                gid = norm(row.get("game_id", ""))
                proj = to_float(row.get("game_projected_points", None))

                if gid and proj is not None:
                    projection_map[gid] = proj
                    rows_loaded += 1

        except Exception:
            log.write(f"\nERROR reading cleaned file: {path}\n")
            log.write(traceback.format_exc())
            log.write("\n")

    log.write(f"Cleaned files scanned: {files_scanned}\n")
    log.write(f"Cleaned files used (have game_projected_points): {files_used}\n")
    log.write(f"Cleaned files skipped (no game_projected_points): {files_skipped_no_column}\n")
    log.write(f"Projection rows loaded: {rows_loaded}\n\n")

    return projection_map

# =========================
# CORE
# =========================

def process_files():

    timestamp = datetime.utcnow().isoformat() + "Z"

    with open(ERROR_LOG, "w") as log:

        log.write(f"=== WINNERS_04 RUN @ {timestamp} ===\n\n")

        projection_map = build_projection_map(log)

        winners_files = sorted(glob.glob(str(INPUT_DIR / "winners_*.csv")))

        log.write(f"Winners files found: {len(winners_files)}\n\n")

        files_processed = 0
        rows_processed = 0
        rows_candidate = 0
        rows_updated = 0
        rows_missing_projection = 0
        rows_missing_total = 0
        rows_bad_total = 0
        errors = 0

        for file_path in winners_files:
            try:
                df = pd.read_csv(file_path)

                if "proj_total" not in df.columns:
                    df["proj_total"] = ""

                if "total_diff" not in df.columns:
                    df["total_diff"] = ""

                for idx, row in df.iterrows():
                    rows_processed += 1

                    bet_value = norm(row.get("bet", ""))

                    if bet_value not in ("over_bet", "under_bet"):
                        continue

                    rows_candidate += 1

                    game_id = norm(row.get("game_id", ""))
                    proj_total = projection_map.get(game_id)

                    if proj_total is None:
                        rows_missing_projection += 1
                        continue

                    total_val = to_float(row.get("total", None))
                    if total_val is None:
                        rows_missing_total += 1
                        continue

                    df.at[idx, "proj_total"] = proj_total
                    df.at[idx, "total_diff"] = total_val - proj_total
                    rows_updated += 1

                df.to_csv(file_path, index=False)

                files_processed += 1
                log.write(f"Processed: {file_path} | rows={len(df)}\n")

            except Exception:
                errors += 1
                log.write(f"\nERROR processing {file_path}\n")
                log.write(traceback.format_exc())
                log.write("\n")

        log.write("\n=== SUMMARY ===\n")
        log.write(f"Files processed: {files_processed}\n")
        log.write(f"Rows processed: {rows_processed}\n")
        log.write(f"Rows eligible (over_bet/under_bet): {rows_candidate}\n")
        log.write(f"Rows updated: {rows_updated}\n")
        log.write(f"Rows missing projection match: {rows_missing_projection}\n")
        log.write(f"Rows missing total value: {rows_missing_total}\n")
        log.write(f"Errors: {errors}\n")

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    process_files()
