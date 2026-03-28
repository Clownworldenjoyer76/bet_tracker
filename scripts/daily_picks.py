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


def build_rows(df, league_value):
    rows = []

    for _, r in df.iterrows():
        row = {
            "league": league_value,
            "game_id": r.get("game_id", ""),
            "game_date": r.get("game_date", ""),
            "game_time": r.get("game_time", ""),
            "home_team": r.get("home_team", ""),
            "away_team": r.get("away_team", ""),
            "bet_side": r.get("bet_side", ""),
            "market_type": r.get("market_type", ""),
            "line": r.get("line", "")
        }
        rows.append(row)

    return rows


def main():
    try:
        date_str = datetime.now().strftime("%Y_%m_%d")

        all_rows = []

        # MLB
        mlb_path = BASEBALL_DIR / f"{date_str}_MLB.csv"
        df = load_csv(mlb_path)
        if not df.empty:
            all_rows.extend(build_rows(df, "NBA"))  # per spec

        # NHL
        nhl_path = HOCKEY_DIR / f"{date_str}_NHL.csv"
        df = load_csv(nhl_path)
        if not df.empty:
            all_rows.extend(build_rows(df, "NHL"))

        # NBA
        df = load_csv(NBA_FILE)
        if not df.empty:
            df = filter_to_date(df, date_str)
            if not df.empty:
                all_rows.extend(build_rows(df, "NBA"))

        # NCAAB
        df = load_csv(NCAAB_FILE)
        if not df.empty:
            df = filter_to_date(df, date_str)
            if not df.empty:
                all_rows.extend(build_rows(df, "NCAAB"))

        if not all_rows:
            log_error("No data found")
            return

        final = pd.DataFrame(all_rows)

        output_file = OUTPUT_DIR / f"{date_str}_daily_picks.csv"
        final.to_csv(output_file, index=False)

    except Exception:
        log_error(traceback.format_exc())


if __name__ == "__main__":
    main()
