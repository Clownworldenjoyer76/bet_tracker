#!/usr/bin/env python3
# scripts/daily_picks.py

import csv
import traceback
from pathlib import Path
from datetime import datetime

date_str = datetime.now().strftime("%Y_%m_%d")

SOURCES = [
    (Path(f"docs/win/baseball/04_select/{date_str}_MLB.csv"), "MLB"),
    (Path(f"docs/win/hockey/04_select/{date_str}_NHL.csv"), "NHL"),
    (Path("docs/win/basketball/04_select/daily_slate/nba_selected.csv"), "NBA"),
    (Path("docs/win/basketball/04_select/daily_slate/ncaab_selected.csv"), "NCAAB"),
]

OUTPUT_PATH = Path(f"docs/win/final_scores/daily_picks/{date_str}_daily_picks.csv")
ERROR_PATH = Path("docs/win/final_scores/errors/daily_picks.txt")

COLUMNS = ["league", "game_id", "game_date", "game_time", "home_team", "away_team", "bet_side", "market_type", "line"]


def log_error(msg):
    ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ERROR_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def main():
    rows = []

    for path, league in SOURCES:
        if not path.exists():
            continue
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

    if not rows:
        log_error("NO DATA FOUND")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error(traceback.format_exc())
