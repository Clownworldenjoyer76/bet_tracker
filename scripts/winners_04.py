#!/usr/bin/env python3

import pandas as pd
import glob
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS (EXACTLY AS GIVEN)
# =========================

INPUT_DIR = Path("docs/win/winners/step_02_1")
OUTPUT_DIR = Path("docs/win/winners/step_02_1")
CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
ERROR_LOG = Path("docs/win/errors/winners_04.txt")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

# =========================
# BUILD PROJECTION MAP
# =========================

def build_projection_map(log):

    projection_map = {}

    cleaned_files = sorted(glob.glob(str(CLEANED_DIR / "*.csv")))

    log.write(f"Cleaned files discovered: {len(cleaned_files)}\n")

    files_with_projection_column = 0
    total_projection_rows_loaded = 0

    for file_path in cleaned_files:
        try:
            df = pd.read_csv(file_path)

            if "game_projected_points" not in df.columns:
                log.write(f"SKIPPED (no game_projected_points column): {file_path}\n")
                continue

            files_with_projection_column += 1

            for _, row in df.iterrows():
                if "game_id" in df.columns:
                    gid = str(row["game_id"]).strip()
                    proj = row["game_projected_points"]

                    if pd.notna(gid) and pd.notna(proj):
                        projection_map[gid] = float(proj)
                        total_projection_rows_loaded += 1

        except Exception as e:
            log.write(f"\nERROR reading cleaned file: {file_path}\n")
            log.write(str(e) + "\n")
            log.write(traceback.format_exc() + "\n")

    log.write(f"\nFiles containing game_projected_points: {files_with_projection_column}\n")
    log.write(f"Total projection rows loaded: {total_projection_rows_loaded}\n\n")

    return projection_map


# =========================
# MAIN PROCESS
# =========================

def process():

    timestamp = datetime.utcnow().isoformat() + "Z"

    with open(ERROR_LOG, "w") as log:

        log.write("=== WINNERS_04 RUN START ===\n")
        log.write(f"Timestamp: {timestamp}\n\n")

        projection_map = build_projection_map(log)

        winners_files = sorted(glob.glob(str(INPUT_DIR / "winners_*.csv")))

        log.write(f"Winners files discovered: {len(winners_files)}\n\n")

        files_processed = 0
        total_rows_processed = 0
        eligible_rows = 0
        rows_with_projection_match = 0
        rows_missing_projection = 0
        rows_missing_total = 0
        rows_updated = 0

        for file_path in winners_files:

            try:
                df = pd.read_csv(file_path)

                # ADD COLUMNS (ALWAYS CREATED)
                df["proj_total"] = ""
                df["total_diff"] = ""

                log.write(f"\nProcessing file: {file_path}\n")
                log.write(f"Rows in file: {len(df)}\n")

                for idx, row in df.iterrows():

                    total_rows_processed += 1

                    bet_value = str(row["bet"]).strip()

                    if bet_value == "over_bet" or bet_value == "under_bet":

                        eligible_rows += 1

                        game_id = str(row["game_id"]).strip()

                        if game_id in projection_map:

                            proj_total = projection_map[game_id]
                            df.at[idx, "proj_total"] = proj_total
                            rows_with_projection_match += 1

                            total_value = row["total"]

                            if pd.notna(total_value):
                                try:
                                    total_float = float(total_value)
                                    df.at[idx, "total_diff"] = total_float - proj_total
                                    rows_updated += 1
                                except:
                                    rows_missing_total += 1
                            else:
                                rows_missing_total += 1

                        else:
                            rows_missing_projection += 1

                df.to_csv(file_path, index=False)

                files_processed += 1

            except Exception as e:
                log.write(f"\nERROR processing winners file: {file_path}\n")
                log.write(str(e) + "\n")
                log.write(traceback.format_exc() + "\n")

        # =========================
        # FINAL SUMMARY
        # =========================

        log.write("\n=== SUMMARY ===\n")
        log.write(f"Files processed: {files_processed}\n")
        log.write(f"Total rows processed: {total_rows_processed}\n")
        log.write(f"Eligible rows (over_bet/under_bet): {eligible_rows}\n")
        log.write(f"Rows with projection match: {rows_with_projection_match}\n")
        log.write(f"Rows missing projection match: {rows_missing_projection}\n")
        log.write(f"Rows missing/invalid total: {rows_missing_total}\n")
        log.write(f"Rows fully updated (proj_total + total_diff): {rows_updated}\n")
        log.write("\n=== RUN COMPLETE ===\n")


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    process()
