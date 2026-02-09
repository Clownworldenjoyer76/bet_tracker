#!/usr/bin/env python3

import csv
from pathlib import Path
from datetime import datetime

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/cleaned")
DUMP_DIR = Path("docs/win/dump/csvs/cleaned")
ERROR_DIR = Path("docs/win/errors")

ERROR_DIR.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ERROR_LOG = ERROR_DIR / f"dk_2_game_id_{TIMESTAMP}.txt"

# =========================
# HELPERS
# =========================

def log_error(msg: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def norm(s: str) -> str:
    if s is None:
        return ""
    return " ".join(str(s).split())

def load_dump_index(league: str):
    """
    Build lookup:
    (date, away_team, home_team) -> game_id
    """
    index = {}

    for path in DUMP_DIR.glob(f"{league}_*.csv"):
        parts = path.stem.split("_")
        if len(parts) < 4:
            continue

        year, month, day = parts[-3:]
        date = f"{year}_{month}_{day}"

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game_id = row.get("game_id", "")
                if not game_id:
                    continue

                away = norm(row.get("away_team"))
                home = norm(row.get("home_team"))

                index[(date, away, home)] = game_id

    return index

# =========================
# CORE LOGIC
# =========================

def process_file(path: Path):
    # dk_{league}_{market}_{YYYY}_{MM}_{DD}.csv
    parts = path.stem.split("_")
    if len(parts) < 6:
        return

    _, league, market, year, month, day = parts
    date = f"{year}_{month}_{day}"

    dump_index = load_dump_index(league)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "game_id" not in fieldnames:
        fieldnames.append("game_id")

    updated_rows = []

    for row in rows:
        away = norm(row.get("away_team"))
        home = norm(row.get("home_team"))

        game_id = dump_index.get((date, away, home), "")
        row["game_id"] = game_id

        if not game_id:
            log_error(
                f"{path.name} | league={league} | date={date} | away={away} | home={home}"
            )

        updated_rows.append(row)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

# =========================
# MAIN
# =========================

def main():
    patterns = [
        "dk_*_moneyline_*.csv",
        "dk_*_spreads_*.csv",
        "dk_*_totals_*.csv",
    ]

    for pattern in patterns:
        for file in INPUT_DIR.glob(pattern):
            process_file(file)

if __name__ == "__main__":
    main()
