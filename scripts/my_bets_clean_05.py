# scripts/my_bets_clean_05.py

#!/usr/bin/env python3

import pandas as pd
import glob
from pathlib import Path
from datetime import datetime
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
# LOG (OVERWRITE ALWAYS)
# =========================

def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

with open(ERROR_LOG, "w", encoding="utf-8") as f:
    f.write(f"=== MY_BETS_CLEAN_05 RUN @ {datetime.utcnow().isoformat()}Z ===\n")

# =========================
# LOAD GAMES MASTER
# =========================

def load_games_master():
    files = glob.glob(str(GAMES_MASTER_DIR / "games_*.csv"))
    if not files:
        return pd.DataFrame()

    dfs = []
    for file in files:
        try:
            df = pd.read_csv(file)
            dfs.append(df[["date", "away_team", "home_team", "game_id"]])
        except Exception as e:
            log(f"ERROR loading games master file {file}: {e}")
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

# =========================
# MAIN
# =========================

def process():
    games_df = load_games_master()

    if games_df.empty:
        log("No games_master files found or empty.")
        return

    input_files = glob.glob(str(INPUT_DIR / "juiceReelBets_*.csv"))

    total_files = 0
    total_rows = 0
    total_matched = 0
    total_unmatched = 0

    for file_path in input_files:
        try:
            total_files += 1
            df = pd.read_csv(file_path)

            original_rows = len(df)
            total_rows += original_rows

            merged = df.merge(
                games_df,
                on=["date", "away_team", "home_team"],
                how="left"
            )

            matched = merged["game_id"].notna().sum()
            unmatched = merged["game_id"].isna().sum()

            total_matched += matched
            total_unmatched += unmatched

            # Drop time column if exists
            if "time" in merged.columns:
                merged = merged.drop(columns=["time"])

            # Output schema
            output_cols = [
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
                "bet"
            ]

            for col in output_cols:
                if col not in merged.columns:
                    merged[col] = ""

            merged = merged[output_cols]

            output_path = OUTPUT_DIR / Path(file_path).name
            merged.to_csv(output_path, index=False)

            log(f"Wrote {output_path} | rows={original_rows} matched={matched} unmatched={unmatched}")

        except Exception:
            log(f"ERROR processing {file_path}")
            log(traceback.format_exc())

    log(f"Files processed: {total_files}")
    log(f"Rows processed: {total_rows}")
    log(f"Rows matched: {total_matched}")
    log(f"Rows unmatched: {total_unmatched}")

# =========================
# RUN
# =========================

if __name__ == "__main__":
    process()
