# scripts/dk_02.py

#!/usr/bin/env python3

import csv
from pathlib import Path
import pandas as pd

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/cleaned")
GAMES_MASTER_DIR = Path("docs/win/games_master")

ERROR_DIR = Path("docs/win/errors/02_dk_prep")
ERROR_LOG = ERROR_DIR / "dk_02_game_id.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def log(msg: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def norm(s: str) -> str:
    return " ".join(str(s).split()) if s else ""

def load_games_master_index():
    files = GAMES_MASTER_DIR.glob("games_*.csv")
    df = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)

    index = {}
    for _, r in df.iterrows():
        key = (r["date"], norm(r["away_team"]), norm(r["home_team"]))
        index[key] = r["game_id"]

    return index

# =========================
# CORE
# =========================

def process_file(path: Path, gm_index):
    rows_in = rows_matched = 0

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "game_id" not in fieldnames:
        fieldnames.append("game_id")

    parts = path.stem.split("_")
    if len(parts) < 6:
        log(f"SKIPPED (bad filename): {path.name}")
        return

    _, league, _, year, month, day = parts
    date = f"{year}_{month}_{day}"

    for row in rows:
        rows_in += 1
        away = norm(row.get("away_team"))
        home = norm(row.get("home_team"))

        gid = gm_index.get((date, away, home), "")
        row["game_id"] = gid

        if gid:
            rows_matched += 1
        else:
            log(f"NO_MATCH | {path.name} | {date} | {away} vs {home}")

    if rows_in and rows_matched / rows_in < 0.9:
        raise RuntimeError(
            f"Low game_id match rate in {path.name}: {rows_matched}/{rows_in}"
        )

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log(f"{path.name} | rows={rows_in} matched={rows_matched}")

# =========================
# MAIN
# =========================

def main():
    log("DK_02 START")
    gm_index = load_games_master_index()

    for path in INPUT_DIR.glob("dk_*_*.csv"):
        process_file(path, gm_index)

    log("DK_02 END\n")

if __name__ == "__main__":
    main()
