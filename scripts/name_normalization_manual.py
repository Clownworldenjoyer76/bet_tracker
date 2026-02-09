# scripts/name_normalization_manual.py

#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/cleaned")
MAP_DIR = Path("mappings")
NO_MAP_DIR = Path("mappings/need_map")
NO_MAP_PATH = NO_MAP_DIR / "dump_no_map.csv"

ERROR_DIR = Path("docs/win/errors/02_dk_prep")
ERROR_LOG = ERROR_DIR / "name_normalization_manual.txt"

NO_MAP_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLS = ("team", "opponent", "away_team", "home_team")

# =========================
# HELPERS
# =========================

def load_team_map_for_league(league: str):
    map_path = MAP_DIR / f"team_map_{league}.csv"
    if not map_path.exists():
        return {}, set()

    df = pd.read_csv(map_path, dtype=str)
    team_map = {}
    canonical_set = set()

    for _, row in df.iterrows():
        alias = str(row["alias"]).strip()
        canonical = str(row["canonical_team"]).strip()
        team_map[alias] = canonical
        canonical_set.add(canonical)

    return team_map, canonical_set

def normalize_team(val, team_map, canonical_set, unmapped, league):
    if pd.isna(val):
        return val

    v = str(val).strip()

    if v in canonical_set:
        return v

    if v in team_map:
        return team_map[v]

    unmapped.add((v, league))
    return v

# =========================
# MAIN
# =========================

def main():
    unmapped = set()
    files_processed = 0
    values_updated = 0

    try:
        for file_path in INPUT_DIR.glob("dk_*_*.csv"):
            df = pd.read_csv(file_path, dtype=str)

            if "league" not in df.columns:
                continue

            league = str(df["league"].iloc[0]).strip()
            team_map, canonical_set = load_team_map_for_league(league)

            if not team_map:
                continue

            updated = False

            for col in TARGET_COLS:
                if col not in df.columns:
                    continue

                new_vals = []
                for v in df[col]:
                    new_v = normalize_team(
                        v, team_map, canonical_set, unmapped, league
                    )
                    if new_v != v:
                        values_updated += 1
                        updated = True
                    new_vals.append(new_v)

                df[col] = new_vals

            if updated:
                df.to_csv(file_path, index=False)

            files_processed += 1

        if unmapped:
            pd.DataFrame(
                sorted(unmapped),
                columns=["team", "league"]
            ).to_csv(NO_MAP_PATH, index=False)

        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write("NAME NORMALIZATION MANUAL SUMMARY\n")
            f.write("=================================\n")
            f.write(f"Files processed: {files_processed}\n")
            f.write(f"Values updated: {values_updated}\n")
            f.write(f"Unmapped values: {len(unmapped)}\n")

    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())

if __name__ == "__main__":
    main()
