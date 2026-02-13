# scripts/my_bets_clean_01.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/my_bets/raw")
OUTPUT_DIR = Path("docs/win/my_bets/step_01")
ERROR_DIR = Path("docs/win/errors/01_raw")
ERROR_LOG = ERROR_DIR / "my_bets_clean_01.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONSTANTS
# =========================

COLUMNS_TO_DROP = [
    "date_settled",
    "date_synced",
    "if_freeplay_then_amount_actually_at_risk",
    "is_odds_boosted",
    "if_duration_bet",
    "bet_tag_details",
]

# =========================
# HELPERS
# =========================

def parse_date_time(date_placed_value):
    """
    Input example:
    2026-02-10 11:31:42.477+00

    Returns:
    file_date = 2026_02_10
    date = 2026_02_10
    time = 11:31:42
    """
    try:
        base = str(date_placed_value).split("+")[0]
        dt = datetime.strptime(base, "%Y-%m-%d %H:%M:%S.%f")
        file_date = dt.strftime("%Y_%m_%d")
        date_str = dt.strftime("%Y_%m_%d")
        time_str = dt.strftime("%H:%M:%S")
        return file_date, date_str, time_str
    except Exception:
        return None, None, None

# =========================
# MAIN
# =========================

def process_files():
    summary_lines = []
    summary_lines.append(f"=== MY_BETS_CLEAN_01 RUN @ {datetime.utcnow().isoformat()}Z ===\n")

    files = sorted(INPUT_DIR.glob("*.csv"))

    if not files:
        summary_lines.append("No input files found.\n")
        ERROR_LOG.write_text("".join(summary_lines))
        return

    for file_path in files:
        try:
            df = pd.read_csv(file_path)
            rows_in = len(df)

            # 1. Remove sportsbook = Fliff
            if "sportsbook" in df.columns:
                df = df[df["sportsbook"] != "Fliff"]

            # 2. Remove number_of_legs != 1
            if "number_of_legs" in df.columns:
                df = df[df["number_of_legs"] == 1]

            # 3. Drop unwanted columns (only if present)
            drop_cols = [c for c in COLUMNS_TO_DROP if c in df.columns]
            df = df.drop(columns=drop_cols, errors="ignore")

            # 4. Create league, date, time columns
            if "date_placed" not in df.columns:
                raise ValueError("Missing required column: date_placed")

            file_dates = []
            date_vals = []
            time_vals = []

            for val in df["date_placed"]:
                file_date, date_str, time_str = parse_date_time(val)
                file_dates.append(file_date)
                date_vals.append(date_str)
                time_vals.append(time_str)

            df["league"] = ""
            df["date"] = date_vals
            df["time"] = time_vals

            # 5. Create empty columns
            df["away_team"] = ""
            df["home_team"] = ""
            df["game_id"] = ""
            df["team_1"] = ""
            df["team_2"] = ""

            # Determine output filename from first valid date_placed
            valid_file_dates = [fd for fd in file_dates if fd is not None]
            if not valid_file_dates:
                raise ValueError("Unable to parse any date_placed values.")

            output_date = valid_file_dates[0]
            output_filename = f"{output_date}_bets.csv"
            output_path = OUTPUT_DIR / output_filename

            df.to_csv(output_path, index=False)

            summary_lines.append(
                f"{file_path.name} | rows_in={rows_in} rows_out={len(df)} -> {output_filename}\n"
            )

        except Exception as e:
            summary_lines.append(f"ERROR processing {file_path.name}\n")
            summary_lines.append(str(e) + "\n")
            summary_lines.append(traceback.format_exc() + "\n")

    ERROR_LOG.write_text("".join(summary_lines))


if __name__ == "__main__":
    process_files()
