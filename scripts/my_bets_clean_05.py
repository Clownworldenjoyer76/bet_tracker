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
WINNERS_DIR = Path("docs/win/winners/step_03")
OUTPUT_DIR = Path("docs/win/my_bets/step_04")
ERROR_DIR = Path("docs/win/errors/01_raw")
ERROR_LOG = ERROR_DIR / "my_bets_clean_05.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOAD HELPERS
# =========================

def load_games_master():
    files = glob.glob(str(GAMES_MASTER_DIR / "games_*.csv"))
    frames = []
    for f in files:
        df = pd.read_csv(f, dtype={"game_id": str})
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_winners():
    files = glob.glob(str(WINNERS_DIR / "winners_*.csv"))
    frames = []
    for f in files:
        df = pd.read_csv(f, dtype={"game_id": str})
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# =========================
# MAIN
# =========================

def process_files():
    files = glob.glob(str(INPUT_DIR / "juiceReelBets_*.csv"))

    games_master = load_games_master()
    winners = load_winners()

    files_processed = 0
    rows_total = 0
    rows_matched_games = 0
    rows_matched_winners = 0
    rows_unmatched_games = 0
    rows_unmatched_winners = 0

    try:
        for file_path in files:
            df = pd.read_csv(file_path)
            rows_total += len(df)

            # Remove time column
            if "time" in df.columns:
                df = df.drop(columns=["time"])

            # Ensure merge keys are strings
            df["date"] = df["date"].astype(str)
            df["away_team"] = df["away_team"].astype(str)
            df["home_team"] = df["home_team"].astype(str)

            games_master["date"] = games_master["date"].astype(str)
            games_master["away_team"] = games_master["away_team"].astype(str)
            games_master["home_team"] = games_master["home_team"].astype(str)

            # =========================
            # STEP 1: MATCH TO GAMES_MASTER
            # =========================

            merged = df.merge(
                games_master[["date", "away_team", "home_team", "game_id"]],
                how="left",
                on=["date", "away_team", "home_team"]
            )

            # Force game_id to string (prevents float issues)
            merged["game_id"] = merged["game_id"].astype(str)

            rows_matched_games += merged["game_id"].ne("nan").sum()
            rows_unmatched_games += merged["game_id"].eq("nan").sum()

            # =========================
            # STEP 2: MATCH TO WINNERS
            # =========================

            edge_fields = [
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

            winners_subset = winners[["game_id"] + edge_fields].copy()
            winners_subset["game_id"] = winners_subset["game_id"].astype(str)

            merged = merged.merge(
                winners_subset,
                how="left",
                on="game_id"
            )

            rows_matched_winners += merged["home_ml_edge"].notna().sum()
            rows_unmatched_winners += merged["home_ml_edge"].isna().sum()

            # =========================
            # OUTPUT ORDER
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
            log.write(f"Rows processed: {rows_total}\n\n")
            log.write(f"Rows matched to games_master: {rows_matched_games}\n")
            log.write(f"Rows NOT matched to games_master: {rows_unmatched_games}\n\n")
            log.write(f"Rows matched to winners: {rows_matched_winners}\n")
            log.write(f"Rows NOT matched to winners: {rows_unmatched_winners}\n")

    except Exception as e:
        with open(ERROR_LOG, "w") as log:
            log.write("ERROR DURING PROCESSING\n")
            log.write(str(e) + "\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    process_files()
