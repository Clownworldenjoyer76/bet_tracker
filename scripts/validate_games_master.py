#!/usr/bin/env python3

import sys
from pathlib import Path
import pandas as pd

# =========================
# PATHS
# =========================

GAMES_MASTER_DIR = Path("docs/win/games_master")
ERROR_DIR = Path("docs/win/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# Only validate active pipeline outputs
VALIDATE_DIRS = [
    Path("docs/win/dump"),
    Path("docs/win/manual"),
    Path("docs/win/final"),
]

REQUIRED_COLUMNS = {"game_id", "away_team", "home_team"}

# =========================
# LOAD GAMES MASTER
# =========================

def load_games_master():
    files = sorted(GAMES_MASTER_DIR.glob("games_*.csv"))
    if not files:
        raise RuntimeError("No games_master files found")

    df = pd.concat(
        [pd.read_csv(f, dtype=str) for f in files],
        ignore_index=True
    )

    required = {"game_id", "league", "date", "away_team", "home_team"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"games_master missing columns: {missing}")

    return df.set_index("game_id")

# =========================
# VALIDATION CORE
# =========================

def validate_file(path: Path, games_master: pd.DataFrame):
    df = pd.read_csv(path, dtype=str)

    # Skip files that cannot possibly be validated
    if not REQUIRED_COLUMNS.issubset(df.columns):
        return []

    errors = []

    for i, row in df.iterrows():
        gid = row["game_id"]

        if gid not in games_master.index:
            errors.append((path.as_posix(), i, gid, "game_id_not_found"))
            continue

        gm = games_master.loc[gid]

        if row["away_team"] != gm["away_team"]:
            errors.append((path.as_posix(), i, gid, "away_team_mismatch"))

        if row["home_team"] != gm["home_team"]:
            errors.append((path.as_posix(), i, gid, "home_team_mismatch"))

    return errors

# =========================
# MAIN
# =========================

def main():
    games_master = load_games_master()
    error_rows = []

    for base_dir in VALIDATE_DIRS:
        if not base_dir.exists():
            continue

        for csv_path in base_dir.rglob("*.csv"):
            if "games_master" in csv_path.as_posix():
                continue

            errs = validate_file(csv_path, games_master)
            if errs:
                error_rows.extend(errs)

    if error_rows:
        err_df = pd.DataFrame(
            error_rows,
            columns=["file", "row", "game_id", "error"]
        )
        out = ERROR_DIR / "games_master_validation_errors.csv"
        err_df.to_csv(out, index=False)

        raise RuntimeError(
            f"Games master validation failed ({len(err_df)} errors)"
        )

    print("games_master validation passed")

if __name__ == "__main__":
    main()
