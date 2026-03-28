#!/usr/bin/env python3
# scripts/daily_picks.py

import csv
import traceback
from pathlib import Path
from datetime import datetime

BASEBALL_DIR = Path("docs/win/baseball/04_select")
HOCKEY_DIR = Path("docs/win/hockey/04_select")
NBA_FILE = Path("docs/win/basketball/04_select/daily_slate/nba_selected.csv")
NCAAB_FILE = Path("docs/win/basketball/04_select/daily_slate/ncaab_selected.csv")

OUTPUT_DIR = Path("docs/win/final_scores/daily_picks")
ERROR_DIR = Path("docs/win/final_scores/errors")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "daily_picks.txt"

OUTPUT_COLUMNS = [
    "league",
    "game_id",
    "game_date",
    "game_time",
    "home_team",
    "away_team",
    "bet_side",
    "market_type",
    "line",
]


def log_error(msg: str) -> None:
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def read_csv_rows(path: Path):
    try:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        log_error(f"FAILED TO READ {path}\n{traceback.format_exc()}")
        return []


def normalize_date_value(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_output_rows(source_rows, forced_league: str, target_date_dashes: str = None):
    """
    target_date_dashes: date string in YYYY-MM-DD format (matches game_date values in CSV).
    Pass None to include all rows (baseball/hockey files are already date-scoped by filename).
    """
    out = []

    for src in source_rows:
        game_date = normalize_date_value(src.get("game_date", ""))

        if target_date_dashes is not None and game_date != target_date_dashes:
            continue

        out.append({
            "league": forced_league,
            "game_id": src.get("game_id", ""),
            "game_date": src.get("game_date", ""),
            "game_time": src.get("game_time", ""),
            "home_team": src.get("home_team", ""),
            "away_team": src.get("away_team", ""),
            "bet_side": src.get("bet_side", ""),
            "market_type": src.get("market_type", ""),
            "line": src.get("line", ""),
        })

    return out


def write_output(path: Path, rows) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    try:
        now = datetime.now()
        date_underscores = now.strftime("%Y_%m_%d")   # e.g. 2026_03_28  — used in filenames
        date_dashes = now.strftime("%Y-%m-%d")        # e.g. 2026-03-28  — matches game_date in CSVs

        baseball_path = BASEBALL_DIR / f"{date_underscores}_MLB.csv"
        hockey_path = HOCKEY_DIR / f"{date_underscores}_NHL.csv"

        final_rows = []

        # Baseball file -> league = MLB
        baseball_rows = read_csv_rows(baseball_path)
        final_rows.extend(build_output_rows(baseball_rows, "MLB"))

        # Hockey file -> league = NHL
        hockey_rows = read_csv_rows(hockey_path)
        final_rows.extend(build_output_rows(hockey_rows, "NHL"))

        # NBA selected -> filter to today's date
        nba_rows = read_csv_rows(NBA_FILE)
        final_rows.extend(build_output_rows(nba_rows, "NBA", target_date_dashes=date_dashes))

        # NCAAB selected -> filter to today's date
        ncaab_rows = read_csv_rows(NCAAB_FILE)
        final_rows.extend(build_output_rows(ncaab_rows, "NCAAB", target_date_dashes=date_dashes))

        if not final_rows:
            log_error("NO DATA FOUND")
            return

        output_path = OUTPUT_DIR / f"{date_underscores}_daily_picks.csv"
        write_output(output_path, final_rows)  # "w" mode always overwrites

    except Exception:
        log_error(traceback.format_exc())


if __name__ == "__main__":
    main()
