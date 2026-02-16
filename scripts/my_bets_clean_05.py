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
# LOAD GAMES MASTER
# =========================

def load_games_master():
    files = glob.glob(str(GAMES_MASTER_DIR / "games_*.csv"))
    frames = []
    for f in files:
        df = pd.read_csv(f)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# =========================
# MAIN
# =========================

def process_files():
    files = glob.glob(str(INPUT_DIR / "juiceReelBets_*.csv"))
    games_master = load_games_master()

    files_processed = 0
    rows_total = 0
    rows_matched = 0
    rows_unmatched = 0

    try:
        if "game_id" not in games_master.columns:
            raise ValueError("games_master does not contain 'game_id' column")

        for file_path in files:
            df = pd.read_csv(file_path)
            rows_total += len(df)

            # Remove time column
            if "time" in df.columns:
                df = df.drop(columns=["time"])

            # Ensure merge keys are strings
            for col in ["date", "away_team", "home_team"]:
                df[col] = df[col].astype(str)
                games_master[col] = games_master[col].astype(str)

            # =========================
            # MATCH TO GAMES_MASTER
            # =========================

            merged = df.merge(
                games_master[["date", "away_team", "home_team", "game_id"]],
                how="left",
                on=["date", "away_team", "home_team"]
            )

            if "game_id" not in merged.columns:
                merged["game_id"] = ""

            merged["game_id"] = merged["game_id"].fillna("").astype(str)

            rows_matched += (merged["game_id"] != "").sum()
            rows_unmatched += (merged["game_id"] == "").sum()

            # =========================
            # OUTPUT ORDER (UNCHANGED)
            # =========================

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

            # Ensure columns exist
            for col in output_columns:
                if col not in merged.columns:
                    merged[col] = ""

            merged = merged[output_columns]

            # Write output
            output_path = OUTPUT_DIR / Path(file_path).name
            merged.to_csv(output_path, index=False)

            files_processed += 1

        # =========================
        # SUMMARY LOG
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
