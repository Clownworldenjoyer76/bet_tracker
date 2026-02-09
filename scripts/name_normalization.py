#scripts/name_normalization.py

#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import traceback
import re

# =========================
# PATHS
# =========================

MANUAL_DIR = Path("docs/win/manual")
FIRST_DIR = Path("docs/win/manual/first")
DUMP_DIR = Path("docs/win/dump/csvs/cleaned")

MAP_DIR = Path("mappings")

NO_MAP_DIR = Path("mappings/need_map")
NO_MAP_PATH = NO_MAP_DIR / "no_map.csv"

ERROR_DIR = Path("docs/win/errors")
ERROR_LOG = ERROR_DIR / "name_normalization.txt"

NO_MAP_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def norm(s: str) -> str:
    if pd.isna(s):
        return s
    s = str(s).replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def base_league(lg: str) -> str:
    return norm(lg.split("_")[0])

# =========================
# LOAD MAPS
# =========================

def load_team_maps():
    team_map = {}
    canonical_sets = {}

    for map_file in MAP_DIR.glob("team_map_*.csv"):
        df = pd.read_csv(map_file, dtype=str)

        for _, row in df.iterrows():
            lg = base_league(row["league"])
            alias = norm(row["alias"])
            canonical = norm(row["canonical_team"])

            team_map.setdefault(lg, {})[alias] = canonical
            canonical_sets.setdefault(lg, set()).add(canonical)

    return team_map, canonical_sets

# =========================
# NORMALIZATION CORE
# =========================

def normalize_value(val, lg, team_map, canonical_sets, unmapped, nan_counter):
    if pd.isna(val):
        nan_counter["nan_values"] += 1
        return val

    lg = base_league(lg)
    v = norm(val)

    if v in canonical_sets.get(lg, set()):
        return v

    if v in team_map.get(lg, {}):
        return team_map[lg][v]

    unmapped.add((v, lg))
    return v

# =========================
# MAIN
# =========================

def main():
    try:
        global team_map, canonical_sets, unmapped
        team_map, canonical_sets = load_team_maps()
        unmapped = set()

        nan_counter = {"nan_values": 0}
        skipped_files = []
        skipped_columns = []
        file_counts = {
            "manual": 0,
            "manual_first": 0,
            "dump_cleaned": 0,
        }

        # MANUAL ROOT
        for file_path in MANUAL_DIR.glob("*.csv"):
            file_counts["manual"] += 1
            df = pd.read_csv(file_path, dtype=str)

            if "league" not in df.columns:
                skipped_files.append((str(file_path), "missing league column"))
                continue

            for col in ("team", "opponent"):
                if col not in df.columns:
                    skipped_columns.append((str(file_path), col))
                    continue

                df[col] = [
                    normalize_value(v, lg, team_map, canonical_sets, unmapped, nan_counter)
                    for v, lg in zip(df[col], df["league"])
                ]

            df.to_csv(file_path, index=False)

        # MANUAL / FIRST
        for file_path in FIRST_DIR.glob("*.csv"):
            file_counts["manual_first"] += 1
            lg = file_path.stem.split("_")[1]
            df = pd.read_csv(file_path, dtype=str)

            for col in ("team", "opponent"):
                if col not in df.columns:
                    skipped_columns.append((str(file_path), col))
                    continue

                df[col] = df[col].apply(
                    lambda v: normalize_value(
                        v, lg, team_map, canonical_sets, unmapped, nan_counter
                    )
                )

            df.to_csv(file_path, index=False)

        # DUMP FILES
        for file_pat_
