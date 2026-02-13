#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback
import glob

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/my_bets/step_02")
GAMES_MASTER_DIR = Path("docs/win/games_master")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
ERROR_DIR = Path("docs/win/errors/01_raw")
ERROR_LOG = ERROR_DIR / "my_bets_clean_03.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# MAIN
# =========================

def process_files():
    summary_lines = []
    summary_lines.append(f"=== MY_BETS_CLEAN_03 RUN @ {datetime.utcnow().isoformat()}Z ===\n")

    files = sorted(INPUT_DIR.glob("*_bets.csv"))

    if not files:
        summary_lines.append("No input files found.\n")
        ERROR_LOG.write_text("".join(summary_lines))
        return

    # -------------------------
    # Load normalized data once
    # -------------------------
    normalized_files = glob.glob(str(NORMALIZED_DIR / "*.csv"))
    normalized_df_list = []

    for nf in normalized_files:
        try:
            df = pd.read_csv(nf)
            if {"date", "league", "game_id"}.issubset(df.columns):
                df["league"] = df["league"].astype(str).str.lower()
                normalized_df_list.append(df[["date", "league", "game_id"]])
        except Exception:
            continue

    if normalized_df_list:
        normalized_all = pd.concat(normalized_df_list, ignore_index=True)
    else:
        normalized_all = pd.DataFrame(columns=["date", "league", "game_id"])

    for file_path in files:
        try:
            bets_df = pd.read_csv(file_path)
            rows_in = len(bets_df)

            if rows_in == 0:
                summary_lines.append(f"{file_path.name} | empty file\n")
                continue

            required_cols = ["date", "league", "away_team", "home_team"]
            for col in required_cols:
                if col not in bets_df.columns:
                    raise ValueError(f"Missing required column: {col}")

            # Normalize league to base (nba, ncaab, etc.)
            bets_df["league_base"] = bets_df["league"].astype(str).str.split("_").str[0].str.lower()

            unique_dates = bets_df["date"].dropna().unique()

            if len(unique_dates) != 1:
                raise ValueError(f"Expected exactly one date per file. Found: {unique_dates}")

            file_date = unique_dates[0]
            games_file = GAMES_MASTER_DIR / f"games_{file_date}.csv"

            if not games_file.exists():
                summary_lines.append(f"{file_path.name} | games file not found: games_{file_date}.csv\n")
                continue

            games_df = pd.read_csv(games_file)
            games_df["league"] = games_df["league"].astype(str).str.lower()

            merged = bets_df.merge(
                games_df,
                left_on=["date", "league_base", "away_team", "home_team"],
                right_on=["date", "league", "away_team", "home_team"],
                how="left",
                suffixes=("", "_gm"),
            )

            matched = merged["game_id_gm"].notna().sum()
            unmatched = rows_in - matched

            duplicate_matches = merged.duplicated(
                subset=["books_bet_id"], keep=False
            ).sum()

            bets_df["game_id"] = merged["game_id_gm"]
            bets_df.drop(columns=["league_base"], inplace=True)

            # -------------------------------------------------
            # NEW: Overwrite date from normalized by game_id
            # -------------------------------------------------

            if not normalized_all.empty and "game_id" in bets_df.columns:
                bets_df["league_lower"] = bets_df["league"].astype(str).str.lower()

                date_merge = bets_df.merge(
                    normalized_all,
                    left_on=["game_id", "league_lower"],
                    right_on=["game_id", "league"],
                    how="left",
                    suffixes=("", "_norm"),
                )

                updated_dates = date_merge["date_norm"].notna().sum()

                bets_df["date"] = date_merge["date_norm"].combine_first(bets_df["date"])
                bets_df.drop(columns=["league_lower"], inplace=True)

                summary_lines.append(f"{file_path.name} | date_updates={updated_dates}\n")

            bets_df.to_csv(file_path, index=False)

            summary_lines.append(
                f"{file_path.name} | rows={rows_in} matched={matched} unmatched={unmatched}\n"
            )

            if unmatched > 0:
                summary_lines.append(f"  -> WARNING: {unmatched} unmatched rows\n")

            if duplicate_matches > 0:
                summary_lines.append(f"  -> WARNING: {duplicate_matches} duplicate merge rows detected\n")

        except Exception as e:
            summary_lines.append(f"ERROR processing {file_path.name}\n")
            summary_lines.append(str(e) + "\n")
            summary_lines.append(traceback.format_exc() + "\n")

    ERROR_LOG.write_text("".join(summary_lines))


if __name__ == "__main__":
    process_files()
