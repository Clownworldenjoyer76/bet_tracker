#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/soccer/02_juice")
OUTPUT_DIR = Path("docs/win/soccer/03_edges")

ERROR_DIR = Path("docs/win/soccer/errors/03_edges")
ERROR_LOG = ERROR_DIR / "compute_edges.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def american_to_decimal(american):
    """Converts American odds (e.g., -110, +150) to Decimal (1.91, 2.50)"""
    if pd.isna(american) or american == "":
        return None

    try:
        val = float(str(american).replace("+", ""))
        if val > 0:
            return 1 + (val / 100.0)
        return 1 + (100.0 / abs(val))
    except (ValueError, ZeroDivisionError):
        return None


def parse_match_time(time_str):
    """Convert '03:05 PM' → datetime object for sorting"""
    if pd.isna(time_str):
        return datetime.max
    try:
        return datetime.strptime(str(time_str).strip(), "%I:%M %p")
    except Exception:
        return datetime.max


# =========================
# CORE
# =========================

def main():

    with open(ERROR_LOG, "w") as log:

        log.write("=== COMPUTE EDGES RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:
            input_files = sorted(INPUT_DIR.glob("soccer_*.csv"))

            if not input_files:
                log.write("No input files found in 02_juice.\n")
                return

            summary = {"files_processed": 0, "rows_processed": 0}

            # Define the markets to check
            # Format: (Suffix/Name, Sportsbook American Col, Model Adjusted Col)
            MARKETS = [
                ("home", "home_american", "home_adjusted_decimal"),
                ("draw", "draw_american", "draw_adjusted_decimal"),
                ("away", "away_american", "away_adjusted_decimal"),
                ("over25", "over25_american", "over25_adjusted_decimal"),
                ("btts", "btts_american", "btts_adjusted_decimal"),
            ]

            for input_path in input_files:
                df = pd.read_csv(input_path)

                if "game_id" not in df.columns:
                    log.write(f"Skipping {input_path.name}: Missing game_id\n")
                    continue

                for label, dk_amer_col, model_adj_col in MARKETS:
                    
                    # Only process if both the sportsbook odds and juiced model odds exist
                    if dk_amer_col in df.columns and model_adj_col in df.columns:
                        
                        # 1. Convert Sportsbook American to Decimal
                        dk_dec_col = f"{label}_dk_decimal"
                        df[dk_dec_col] = df[dk_amer_col].apply(american_to_decimal)

                        # 2. Compute Edge: (Book / Model) - 1
                        edge_pct_col = f"{label}_edge_pct"
                        # Ensure we don't divide by zero or NaN
                        df[edge_pct_col] = (df[dk_dec_col] / df[model_adj_col].astype(float)) - 1
                        
                        # 3. Mark as a Play if edge is positive
                        df[f"{label}_play"] = df[edge_pct_col] > 0
                    else:
                        log.write(f"Market {label} skipped in {input_path.name}: Missing columns.\n")

                # =========================
                # SORT, DEDUPE, & CLEANUP
                # =========================

                if "match_time" in df.columns:
                    df["_sort_time"] = df["match_time"].apply(parse_match_time)
                    df = df.sort_values(by="_sort_time")
                    df = df.drop(columns=["_sort_time"])

                df = df.drop_duplicates(subset=["game_id"])

                output_path = OUTPUT_DIR / input_path.name
                df.to_csv(output_path, index=False)

                log.write(f"Wrote {output_path}\n")
                summary["files_processed"] += 1
                summary["rows_processed"] += len(df)

            log.write("\n=== SUMMARY ===\n")
            log.write(f"Files processed: {summary['files_processed']}\n")
            log.write(f"Rows processed: {summary['rows_processed']}\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())
            raise


if __name__ == "__main__":
    main()
