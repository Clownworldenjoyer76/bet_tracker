#!/usr/bin/env python3
# scripts/daily_picks.py

import csv
import re
import traceback
from pathlib import Path
from datetime import datetime

BASEBALL_DIR = Path("docs/win/baseball/04_select")
HOCKEY_DIR = Path("docs/win/hockey/04_select")
NBA_FILE = Path("docs/win/basketball/04_select/daily_slate/nba_selected.csv")
NCAAB_FILE = Path("docs/win/basketball/04_select/daily_slate/ncaab_selected.csv")

OUTPUT_DIR = Path("docs/win/final_scores/daily_picks")
ERROR_PATH = Path("docs/win/final_scores/errors/daily_picks.txt")

COLUMNS = ["league", "game_id", "game_date", "game_time", "home_team", "away_team", "bet_side", "market_type", "line"]
DATE_RE = re.compile(r"^(\d{4}_\d{2}_\d{2})_")


def log_error(msg):
    ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ERROR_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def read_source(path, league):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rows = []
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
            return rows
    except Exception:
        log_error(f"FAILED TO READ {path}\n{traceback.format_exc()}")
        return []


def get_dated_files(directory, suffix):
    """Return {date_str: path} for all dated files in directory matching suffix."""
    result = {}
    if not directory.exists():
        return result
    for f in directory.iterdir():
        m = DATE_RE.match(f.name)
        if m and f.name.endswith(suffix):
            result[m.group(1)] = f
    return result


def write_output(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    baseball_files = get_dated_files(BASEBALL_DIR, "_MLB.csv")
    hockey_files = get_dated_files(HOCKEY_DIR, "_NHL.csv")

    # collect all dates from baseball and hockey
    all_dates = set(baseball_files.keys()) | set(hockey_files.keys())

    # read basketball files once — group rows by game_date
    nba_by_date = {}
    for row in read_source(NBA_FILE, "NBA"):
        d = row["game_date"].replace("-", "_") if "-" in row["game_date"] else row["game_date"]
        nba_by_date.setdefault(d, []).append(row)

    ncaab_by_date = {}
    for row in read_source(NCAAB_FILE, "NCAAB"):
        d = row["game_date"].replace("-", "_") if "-" in row["game_date"] else row["game_date"]
        ncaab_by_date.setdefault(d, []).append(row)

    # add any dates found only in basketball files
    all_dates |= set(nba_by_date.keys()) | set(ncaab_by_date.keys())

    if not all_dates:
        log_error("NO SOURCE FILES FOUND")
        return

    for date_str in sorted(all_dates):
        rows = []
        rows.extend(read_source(baseball_files.get(date_str, Path("__missing__")), "MLB"))
        rows.extend(read_source(hockey_files.get(date_str, Path("__missing__")), "NHL"))
        rows.extend(nba_by_date.get(date_str, []))
        rows.extend(ncaab_by_date.get(date_str, []))

        if not rows:
            continue

        output_path = OUTPUT_DIR / f"{date_str}_daily_picks.csv"
        write_output(output_path, rows)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error(traceback.format_exc())
