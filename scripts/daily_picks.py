#!/usr/bin/env python3
# scripts/daily_picks.py

import csv
import traceback
from pathlib import Path
from datetime import datetime


OUTPUT_DIR = Path("docs/win/final_scores/daily_picks")
ERROR_PATH = Path("docs/win/final_scores/errors/daily_picks.txt")

COLUMNS = ["league", "game_id", "game_date", "game_time", "home_team", "away_team", "bet_side", "market_type", "line"]


def log_error(msg):
    ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ERROR_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def read_source(path, league, rows):
    if not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rows.append({
                    "league": league,
                    "game_id": row.get("game_id", ""),
                    "game_date": row.get("game_date", ""),
                    "game_time": row.get("game_time", ""),
                    "home_team": row.get("home_team", ""),
                    "away_team": row.get("away_team", ""),
                    "bet_side": row.get("bet_side", ""),
                    "market_type": row.get("market_type", ""),
                    "line": row.get("line", ""),
                })
    except Exception:
        log_error(f"FAILED TO READ {path}\n{traceback.format_exc()}")


def main():
    date_str = datetime.now().strftime("%Y_%m_%d")

    rows = []
    read_source(Path(f"docs/win/baseball/04_select/{date_str}_MLB.csv"), "MLB", rows)
    read_source(Path(f"docs/win/hockey/04_select/{date_str}_NHL.csv"), "NHL", rows)
    read_source(Path("docs/win/basketball/04_select/daily_slate/nba_selected.csv"), "NBA", rows)
    read_source(Path("docs/win/basketball/04_select/daily_slate/ncaab_selected.csv"), "NCAAB", rows)

    if not rows:
        log_error("NO DATA FOUND")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{date_str}_daily_picks.csv"
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error(traceback.format_exc())
