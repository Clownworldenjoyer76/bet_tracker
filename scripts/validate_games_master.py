#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import re
import sys

# =========================
# CONFIGURATION
# =========================

# Validation scope
LATEST_ONLY = True  # set False for historical audit mode

# =========================
# PATHS
# =========================

GAMES_MASTER_DIR = Path("docs/win/games_master")

ERROR_DIR = Path("docs/win/errors/03_dk_iv")
ERROR_LOG = ERROR_DIR / "games_master_validation.txt"
ERROR_CSV = ERROR_DIR / "games_master_validation_errors.csv"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

VALIDATE_DIRS = [
    Path("docs/win/dump"),
    Path("docs/win/manual"),
    Path("docs/win/final"),
]

REQUIRED_COLUMNS = {"game_id", "away_team", "home_team", "date", "league"}

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

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise RuntimeError(f"games_master missing columns: {missing}")

    return df.set_index("game_id")

# =========================
# HELPERS
# =========================

def normalize_id_part(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")

def expected_game_id(row):
    return (
        f"{row['league']}_{row['date']}_"
        f"{normalize_id_part(row['away_team'])}_"
        f"{normalize_id_part(row['home_team'])}"
    )

# =========================
# VALIDATION CORE
# =========================

def validate_file(path: Path, games_master: pd.DataFrame, latest_date: str):
    df = pd.read_csv(path, dtype=str)

    if not REQUIRED_COLUMNS.issubset(df.columns):
        return [], "missing_columns"

    errors = []
    rows_checked = 0
    rows_skipped_date = 0

    for _, row in df.iterrows():
        if LATEST_ONLY and row["date"] != latest_date:
            rows_skipped_date += 1
            continue

        rows_checked += 1
        gid = row["game_id"]

        if gid not in games_master.index:
            errors.append((path.as_posix(), gid, "game_id_not_found"))
            continue

        gm = games_master.loc[gid]

        if gid != expected_game_id(row):
            errors.append((path.as_posix(), gid, "game_id_direction_mismatch"))

        if row["away_team"] != gm["away_team"]:
            errors.append((path.as_posix(), gid, "away_team_mismatch"))

        if row["home_team"] != gm["home_team"]:
            errors.append((path.as_posix(), gid, "home_team_mismatch"))

    return errors, rows_checked, rows_skipped_date

# =========================
# MAIN
# =========================

def main():
    # overwrite logs on every run
    ERROR_LOG.write_text("", encoding="utf-8")
    if ERROR_CSV.exists():
        ERROR_CSV.unlink()

    games_master = load_games_master()
    latest_date = games_master["date"].max()

    error_rows = []
    skipped_files = []
    files_scanned = 0
    total_rows_checked = 0
    total_rows_skipped_date = 0

    for base_dir in VALIDATE_DIRS:
        if not base_dir.exists():
            continue

        for csv_path in base_dir.rglob("*.csv"):
            if "games_master" in csv_path.as_posix():
                continue

            files_scanned += 1
            result = validate_file(csv_path, games_master, latest_date)

            if isinstance(result[1], str):
                skipped_files.append((csv_path.as_posix(), result[1]))
                continue

            errs, rows_checked, rows_skipped = result
            total_rows_checked += rows_checked
            total_rows_skipped_date += rows_skipped

            if errs:
                error_rows.extend(errs)

    # =========================
    # LOGGING
    # =========================

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("GAMES MASTER VALIDATION SUMMARY\n")
        f.write("===============================\n\n")
        f.write(f"Validation mode: {'LATEST_ONLY' if LATEST_ONLY else 'HISTORICAL'}\n")
        f.write(f"Latest date: {latest_date}\n\n")
        f.write(f"Files scanned: {files_scanned}\n")
        f.write(f"Rows checked: {total_rows_checked}\n")
        f.write(f"Rows skipped due to date filter: {total_rows_skipped_date}\n\n")

        if skipped_files:
            f.write("Skipped files:\n")
            for path, reason in skipped_files:
                f.write(f"- {path} ({reason})\n")

    # =========================
    # ERROR OUTPUT
    # =========================

    if error_rows:
        err_df = pd.DataFrame(
            error_rows,
            columns=["file", "game_id", "error"]
        )
        err_df.to_csv(ERROR_CSV, index=False)

        raise RuntimeError(
            f"Games master validation failed ({len(err_df)} errors)"
        )

    print("games_master validation passed")

if __name__ == "__main__":
    main()
