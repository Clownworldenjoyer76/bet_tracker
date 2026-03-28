#!/usr/bin/env python3
# scripts/daily_picks.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

###############################################################
# PATH CONFIG
###############################################################

BASEBALL_DIR = Path("docs/win/baseball/04_select")
HOCKEY_DIR = Path("docs/win/hockey/04_select")
NBA_FILE = Path("docs/win/basketball/04_select/daily_slate/nba_selected.csv")
NCAAB_FILE = Path("docs/win/basketball/04_select/daily_slate/ncaab_selected.csv")

OUTPUT_DIR = Path("docs/win/final_scores/daily_picks")
ERROR_DIR = Path("docs/win/final_scores/errors")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "daily_picks.txt"

###############################################################
# HELPERS
###############################################################

def log_error(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def load_csv(path):
    try:
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()
    except Exception:
        log_error(f"Failed reading {path}\n{traceback.format_exc()}")
        return pd.DataFrame()


def extract_columns(df, league_value):
    cols = [
        "game_id",
        "game_date",
        "game_time",
        "home_team",
        "away_team",
        "bet_side",
        "market_type",
        "line"
    ]

    out = pd.DataFrame()
    out["league"] = league_value

    for c in cols:
        out[c] = df[c] if c in df.columns else ""

    return out


###############################################################
# MAIN
###############################################################

def main():
    try:
        date_str = datetime.now().strftime("%Y_%m_%d")

        baseball_file = BASEBALL_DIR / f"{date_str}_MLB.csv"
        hockey_file = HOCKEY_DIR / f"{date_str}_NHL.csv"

        frames = []

        df_baseball = load_csv(baseball_file)
        if not df_baseball.empty:
            frames.append(extract_columns(df_baseball, "NBA"))

        df_hockey = load_csv(hockey_file)
        if not df_hockey.empty:
            frames.append(extract_columns(df_hockey, "NHL"))

        df_nba = load_csv(NBA_FILE)
        if not df_nba.empty:
            frames.append(extract_columns(df_nba, "NBA"))

        df_ncaab = load_csv(NCAAB_FILE)
        if not df_ncaab.empty:
            frames.append(extract_columns(df_ncaab, "NCAAB"))

        if not frames:
            log_error("No input data found")
            return

        final = pd.concat(frames, ignore_index=True)

        output_file = OUTPUT_DIR / f"{date_str}_daily_picks.csv"
        final.to_csv(output_file, index=False)

    except Exception:
        log_error(traceback.format_exc())


if __name__ == "__main__":
    main()
