#!/usr/bin/env python3
# scripts/daily_picks.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

BASEBALL_DIR = Path("docs/win/baseball/04_select")
HOCKEY_DIR = Path("docs/win/hockey/04_select")
NBA_FILE = Path("docs/win/basketball/04_select/daily_slate/nba_selected.csv")
NCAAB_FILE = Path("docs/win/basketball/04_select/daily_slate/ncaab_selected.csv")

OUTPUT_DIR = Path("docs/win/final_scores/daily_picks")
ERROR_DIR = Path("docs/win/final_scores/errors")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "daily_picks.txt"


def log_error(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def load_csv(path):
    try:
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()
    except Exception:
        log_error(f"{path} load failed\n{traceback.format_exc()}")
        return pd.DataFrame()


def filter_to_date(df, date_str):
    if "game_date" not in df.columns:
        return df
    return df[df["game_date"].astype(str) == date_str]


def build_output(df, league_value):
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

    out = pd.DataFrame(index=df.index)

    # FORCE league value — cannot be blank
    out["league"] = league_value

    # Copy columns EXACTLY as-is from input
    for c in cols:
        if c in df.columns:
            out[c] = df[c].values
        else:
            out[c] = ""

    return out


def main():
    try:
        date_str = datetime.now().strftime("%Y_%m_%d")

        frames = []

        # MLB
        mlb_path = BASEBALL_DIR / f"{date_str}_MLB.csv"
        df = load_csv(mlb_path)
        if not df.empty:
            frames.append(build_output(df, "NBA"))  # per spec

        # NHL
        nhl_path = HOCKEY_DIR / f"{date_str}_NHL.csv"
        df = load_csv(nhl_path)
        if not df.empty:
            frames.append(build_output(df, "NHL"))

        # NBA (FILTERED TO DATE)
        df = load_csv(NBA_FILE)
        if not df.empty:
            df = filter_to_date(df, date_str)
            if not df.empty:
                frames.append(build_output(df, "NBA"))

        # NCAAB (FILTERED TO DATE)
        df = load_csv(NCAAB_FILE)
        if not df.empty:
            df = filter_to_date(df, date_str)
            if not df.empty:
                frames.append(build_output(df, "NCAAB"))

        if not frames:
            log_error("No data found")
            return

        final = pd.concat(frames, ignore_index=True)

        output_file = OUTPUT_DIR / f"{date_str}_daily_picks.csv"
        final.to_csv(output_file, index=False)

    except Exception:
        log_error(traceback.format_exc())


if __name__ == "__main__":
    main()
