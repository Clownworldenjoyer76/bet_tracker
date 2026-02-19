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
NORMALIZED_DIR = Path("docs/win/manual/normalized")
ERROR_LOG = Path("docs/win/errors/winners_04.txt")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def load_totals_projection_map():
    """
    Build dict:
    { game_id : proj_total }
    from all dk_*_totals_*.csv files
    """
    projection_map = {}

    totals_files = glob.glob(str(NORMALIZED_DIR / "dk_*_totals_*.csv"))

    for path in totals_files:
        try:
            df = pd.read_csv(path)

            if "game_id" not in df.columns:
                continue

            if "proj_total" not in df.columns:
                continue

            for _, row in df.iterrows():
                gid = str(row["game_id"])
                proj = row["proj_total"]

                if pd.notna(gid) and pd.notna(proj):
                    projection_map[gid] = proj

        except Exception:
            continue

    return projection_map


# =========================
# CORE
# =========================

def process_files():
    timestamp = datetime.utcnow().isoformat() + "Z"

    files = glob.glob(str(INPUT_DIR / "winners_*.csv"))

    projection_map = load_totals_projection_map()

    files_processed = 0
    rows_processed = 0
    rows_updated = 0
    rows_missing_projection = 0
    errors = 0

    with open(ERROR_LOG, "w") as log:
        log.write(f"=== WINNERS_04 RUN @ {timestamp} ===\n")

        for file_path in files:
            try:
                df = pd.read_csv(file_path)

                if "proj_total" not in df.columns:
                    df["proj_total"] = ""

                if "total_diff" not in df.columns:
                    df["total_diff"] = ""

                for idx, row in df.iterrows():
                    rows_processed += 1

                    bet_value = str(row.get("bet", "")).strip()
                    game_id = str(row.get("game_id", "")).strip()

                    if bet_value in ["over_bet", "under_bet"]:
                        proj_total = projection_map.get(game_id)

                        if proj_total is None:
                            rows_missing_projection += 1
                            continue

                        df.at[idx, "proj_total"] = proj_total

                        try:
                            total_val = float(row.get("total", ""))
                            total_diff = float(total_val) - float(proj_total)
                            df.at[idx, "total_diff"] = total_diff
                            rows_updated += 1
                        except Exception:
                            rows_missing_projection += 1
                            continue

                df.to_csv(file_path, index=False)

                files_processed += 1
                log.write(f"Processed {file_path} | rows={len(df)}\n")

            except Exception as e:
                errors += 1
                log.write(f"\nERROR processing {file_path}\n")
                log.write(traceback.format_exc())
                log.write("\n")

        log.write("\n=== SUMMARY ===\n")
        log.write(f"Files processed: {files_processed}\n")
        log.write(f"Rows processed: {rows_processed}\n")
        log.write(f"Rows updated: {rows_updated}\n")
        log.write(f"Rows missing projection: {rows_missing_projection}\n")
        log.write(f"Errors: {errors}\n")


# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    process_files()
