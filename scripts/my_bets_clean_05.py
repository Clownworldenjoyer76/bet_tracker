# scripts/my_bets_clean_05.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/my_bets/step_03")
GAMES_MASTER_DIR = Path("docs/win/games_master")
OUTPUT_DIR = Path("docs/win/my_bets/step_04")
ERROR_DIR = Path("docs/win/errors/01_raw")
ERROR_LOG = ERROR_DIR / "my_bets_clean_05.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOAD ALL GAMES MASTER FILES
# =========================

def load_games_master():
    files = glob.glob(str(GAMES_MASTER_DIR / "games_*.csv"))
    all_games = []

    for file_path in files:
        df = pd.read_csv(file_path)
        all_games.append(df)

    if all_games:
        master = pd.concat(all_games, ignore_index=True)
    else:
        master = pd.DataFrame()

    return master


# =========================
# MAIN
# =========================

def process_files():
    files = glob.glob(str(INPUT_DIR / "juiceReelBets_*.csv"))
    master = load_games_master()

    files_processed = 0
    rows_total = 0
    rows_matched = 0
    rows_unmatched = 0

    try:
        for file_path in files:
            df = pd.read_csv(file_path)
            rows_total += len(df)

            # Drop time column
            if "time" in df.columns:
                df = df.drop(columns=["time"])

            # Merge on date, away_team, home_team
            merged = df.merge(
                master,
                how="left",
                on=["date", "away_team", "home_team"],
                suffixes=("", "_gm")
            )

            # Count matches
            rows_matched += merged["game_id_gm"].notna().sum()
            rows_unmatched += merged["game_id_gm"].isna().sum()

            # Fill game_id
            merged["game_id"] = merged["game_id_gm"]

            # Columns to pull from games_master after match
            fields_to_fill = [
                "home_ml_edge",
                "away_ml_edge",
                "away_ml_odds",
                "home_ml_odds",
                "away_spread",
                "home_spread",
                "home_spread_edge",
                "away_spread_edge",
                "away_spread_odds",
                "home_spread_odds",
                "over_edge",
                "under_edge",
                "over_odds",
                "under_odds",
                "total",
                "bet",
            ]

            for field in fields_to_fill:
                if f"{field}_gm" in merged.columns:
                    merged[field] = merged[f"{field}_gm"]

            # Remove helper columns from games_master
            drop_cols = [col for col in merged.columns if col.endswith("_gm")]
            merged = merged.drop(columns=drop_cols)

            # Strict output order
            output_columns = [
                "date",
                "game_id",
                "risk_amount",
                "max_potential_win",
                "bet_result",
                "amount_won_or_lost",
                "odds_american",
                "clv_percent",
                "leg_type",
                "bet_on",
                "bet_on_spread_total_number",
                "leg_sport",
                "leg_league",
                "leg_vig",
                "away_team",
                "home_team",
                "league",
                "home_ml_edge",
                "away_ml_edge",
                "away_ml_odds",
                "home_ml_odds",
                "away_spread",
                "home_spread",
                "home_spread_edge",
                "away_spread_edge",
                "away_spread_odds",
                "home_spread_odds",
                "over_edge",
                "under_edge",
                "over_odds",
                "under_odds",
                "total",
                "bet",
            ]

            merged = merged[output_columns]

            # Write output
            output_path = OUTPUT_DIR / Path(file_path).name
            merged.to_csv(output_path, index=False)

            files_processed += 1

        # =========================
        # WRITE SUMMARY LOG (OVERWRITE)
        # =========================

        with open(ERROR_LOG, "w") as log:
            log.write("MY_BETS_CLEAN_05 SUMMARY\n")
            log.write("=========================\n\n")
            log.write(f"Files processed: {files_processed}\n")
            log.write(f"Rows processed: {rows_total}\n")
            log.write(f"Rows matched to games_master: {rows_matched}\n")
            log.write(f"Rows NOT matched: {rows_unmatched}\n")

    except Exception as e:
        with open(ERROR_LOG, "w") as log:
            log.write("ERROR DURING PROCESSING\n")
            log.write(str(e) + "\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    process_files()
