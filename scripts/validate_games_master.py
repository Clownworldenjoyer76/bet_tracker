#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import re
import sys
import argparse

# =========================
# PATHS
# =========================

GAMES_MASTER_DIR = Path("docs/win/games_master")

DEFAULT_ERROR_DIR = Path("docs/win/errors/03_dk_iv")

VALIDATE_DIRS = [
    Path("docs/win/manual/normalized"),
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

def base_league(val: str) -> str:
    for suffix in ("_moneyline", "_totals", "_spreads"):
        if str(val).endswith(suffix):
            return val[: -len(suffix)]
    return str(val).split("_", 1)[0]

def expected_game_id(row):
    lg = base_league(row["league"])
    return (
        f"{lg}_{row['date']}_"
        f"{normalize_id_part(row['away_team'])}_"
        f"{normalize_id_part(row['home_team'])}"
    )

# =========================
# VALIDATION CORE
# =========================

def validate_file(path: Path, games_master: pd.DataFrame):
    df = pd.read_csv(path, dtype=str)

    if not REQUIRED_COLUMNS.issubset(df.columns):
        return [], "missing_columns"

    errors = []
    rows_checked = 0

    for _, row in df.iterrows():
        rows_checked += 1
        gid = row["game_id"]

        if not gid:
            errors.append((path.as_posix(), gid, "empty_game_id"))
            continue

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

    return errors, rows_checked

# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--error-dir",
        type=Path,
        default=DEFAULT_ERROR_DIR,
        help="Directory to write validation logs and error CSVs",
    )
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()

    error_dir = args.error_dir
    error_dir.mkdir(parents=True, exist_ok=True)

    error_log = error_dir / "games_master_validation.txt"
    error_csv = error_dir / "games_master_validation_errors.csv"

    error_log.write_text("", encoding="utf-8")
    if error_csv.exists():
        error_csv.unlink()

    games_master = load_games_master()

    if args.paths:
        paths = [Path(p) for p in args.paths]
    else:
        paths = []
        for base_dir in VALIDATE_DIRS:
            if base_dir.exists():
                paths.extend(base_dir.rglob("*.csv"))

    error_rows = []
    skipped_files = []
    files_scanned = 0
    total_rows_checked = 0

    for csv_path in paths:
        if not csv_path.exists():
            continue
        if "games_master" in csv_path.as_posix():
            continue

        files_scanned += 1
        result = validate_file(csv_path, games_master)

        if isinstance(result[1], str):
            skipped_files.append((csv_path.as_posix(), result[1]))
            continue

        errs, rows_checked = result
        total_rows_checked += rows_checked
        error_rows.extend(errs)

    with open(error_log, "w", encoding="utf-8") as f:
        f.write("GAMES MASTER VALIDATION SUMMARY\n")
        f.write("===============================\n\n")
        f.write(f"Files scanned: {files_scanned}\n")
        f.write(f"Rows checked: {total_rows_checked}\n\n")

        if skipped_files:
            f.write("Skipped files:\n")
            for path, reason in skipped_files:
                f.write(f"- {path} ({reason})\n")

    if error_rows:
        err_df = pd.DataFrame(
            error_rows,
            columns=["file", "game_id", "error"]
        )
        err_df.to_csv(error_csv, index=False)
        raise RuntimeError(
            f"Games master validation failed ({len(err_df)} errors)"
        )

    print("games_master validation passed")

if __name__ == "__main__":
    main()
