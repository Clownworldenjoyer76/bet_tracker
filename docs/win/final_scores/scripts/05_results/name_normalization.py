# docs/win/final_scores/scripts/05_results/name_normalization.py

#!/usr/bin/env python3

import pandas as pd
import glob
from pathlib import Path

# -----------------------------
# DIRECTORIES
# -----------------------------

TARGET_DIRS = [
    ("NBA", "docs/win/basketball/04_select"),
    ("NCAAB", "docs/win/basketball/04_select"),
    ("NHL", "docs/win/hockey/04_select"),

    ("NBA", "docs/win/final_scores/results/nba/final_scores"),
    ("NCAAB", "docs/win/final_scores/results/ncaab/final_scores"),
    ("NHL", "docs/win/final_scores/results/nhl/final_scores"),
]

MAP_FILES = {
    "NBA": "mappings/basketball/team_map_nba.csv",
    "NCAAB": "mappings/basketball/team_map_ncaab.csv",
    "NHL": "mappings/hockey/team_map_hockey.csv",
}

NO_MAP_FILE = Path("mappings/05_no_map/no_team_map.csv")
NO_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)


# -----------------------------
# LOAD TEAM MAPS
# -----------------------------

def load_maps():

    maps = {}

    for market, path in MAP_FILES.items():
        df = pd.read_csv(path)

        df["alias"] = df["alias"].str.strip().str.lower()
        df["canonical_team"] = df["canonical_team"].str.strip()

        maps[market] = dict(zip(df["alias"], df["canonical_team"]))

    return maps


# -----------------------------
# NORMALIZE A FILE
# -----------------------------

def normalize_file(file_path, market, team_map, missing):

    try:

        df = pd.read_csv(file_path)

        if "away_team" not in df.columns or "home_team" not in df.columns:
            return

        updated = False

        for col in ["away_team", "home_team"]:

            normalized = []

            for team in df[col]:

                if pd.isna(team):
                    normalized.append(team)
                    continue

                alias = str(team).strip().lower()

                if alias in team_map:
                    normalized.append(team_map[alias])
                    updated = True
                else:
                    normalized.append(team)

                    missing.add((market, alias))

            df[col] = normalized

        if updated:
            df.to_csv(file_path, index=False)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")


# -----------------------------
# MAIN
# -----------------------------

def main():

    team_maps = load_maps()

    missing = set()

    for market, directory in TARGET_DIRS:

        files = glob.glob(f"{directory}/*.csv")

        if market in ["NBA", "NCAAB"]:
            team_map = team_maps[market]
        else:
            team_map = team_maps["NHL"]

        for file_path in files:

            normalize_file(file_path, market, team_map, missing)

    # -----------------------------
    # WRITE MISSING TEAM MAPS
    # -----------------------------

    if missing:

        df_missing = pd.DataFrame(
            sorted(list(missing)),
            columns=["market", "alias"]
        )

        if NO_MAP_FILE.exists():
            existing = pd.read_csv(NO_MAP_FILE)
            df_missing = pd.concat([existing, df_missing]).drop_duplicates()

        df_missing.to_csv(NO_MAP_FILE, index=False)


if __name__ == "__main__":
    main()
