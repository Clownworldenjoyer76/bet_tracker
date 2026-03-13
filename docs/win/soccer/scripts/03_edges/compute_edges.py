# docs/win/soccer/scripts/03_edges/compute_edges.py
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
    """Convert American odds to decimal odds"""

    if pd.isna(american) or american == "":
        return None

    try:
        val = float(american)

        if val > 0:
            return 1 + (val / 100)
        else:
            return 1 + (100 / abs(val))

    except Exception:
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

            summary = {
                "files_processed": 0,
                "rows_processed": 0
            }

            # =========================================================
            # MARKETS CONFIGURATION
            # =========================================================

            MARKETS = [

                ("home", "home_american", "home_adjusted_decimal"),
                ("draw", "draw_american", "draw_adjusted_decimal"),
                ("away", "away_american", "away_adjusted_decimal"),

                ("over25", "over25_american", "over25_adjusted_decimal"),
                ("under25", "under25_american", "under25_adjusted_decimal"),

                ("btts_yes", "btts_yes_american", "btts_yes_adjusted_decimal"),
                ("btts_no", "btts_no_american", "btts_no_adjusted_decimal"),
            ]

            for input_path in input_files:

                df = pd.read_csv(input_path)

                if "game_id" not in df.columns:
                    log.write(f"Skipping {input_path.name}: Missing game_id\n")
                    continue

                for label, dk_amer_col, model_adj_col in MARKETS:

                    if dk_amer_col in df.columns and model_adj_col in df.columns:

                        # -------------------------
                        # Convert sportsbook odds
                        # -------------------------

                        dk_dec_col = f"{label}_dk_decimal"
                        df[dk_dec_col] = df[dk_amer_col].apply(american_to_decimal)

                        # -------------------------
                        # Sportsbook implied probability
                        # -------------------------

                        dk_prob_col = f"{label}_dk_implied_prob"
                        df[dk_prob_col] = 1 / pd.to_numeric(df[dk_dec_col], errors="coerce")

                        # -------------------------
                        # Compute edge
                        # -------------------------

                        edge_pct_col = f"{label}_edge_pct"

                        book_odds = pd.to_numeric(df[dk_dec_col], errors="coerce")
                        model_odds = pd.to_numeric(df[model_adj_col], errors="coerce")

                        edge = (book_odds / model_odds) - 1

                        df[edge_pct_col] = edge.round(4)

                        # -------------------------
                        # Play signal
                        # -------------------------

                        df[f"{label}_play"] = df[edge_pct_col] > 0

                # =========================
                # SORT & CLEAN
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
