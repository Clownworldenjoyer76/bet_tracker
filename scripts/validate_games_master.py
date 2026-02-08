#!/usr/bin/env python3

import sys
from pathlib import Path
import pandas as pd

GAMES_MASTER_DIR = Path("docs/win/games_master")
ERROR_DIR = Path("docs/win/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

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

def validate_file(path: Path, games_master: pd.DataFrame):
    df = pd.read_csv(path, dtype=str)

    if "game_id" not in df.columns:
        return  # file not subject to validation

    errors = []

    for i, row in df.iterrows():
        gid = row["game_id"]

        if gid not in games_master.index:
            errors.append((path.name, i, gid, "game_id_not_found"))
            continue

        gm = games_master.loc[gid]

        if row.get("away_team") != gm["away_team"]:
            errors.append((path.name, i, gid, "away_team_mismatch"))

        if row.get("home_team") != gm["home_team"]:
            errors.append((path.name, i, gid, "home_team_mismatch"))

    return errors

def main():
    games_master = load_games_master()

    error_rows = []

    for csv_path in Path("docs").rglob("*.csv"):
        if "games_master" in str(csv_path):
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
        raise RuntimeError(f"Games master validation failed ({len(err_df)} errors)")

    print("games_master validation passed")

if __name__ == "__main__":
    main()
