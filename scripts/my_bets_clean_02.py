# scripts/my_bets_clean_02.py

#!/usr/bin/env python3

import pandas as pd
import glob
from pathlib import Path
from datetime import datetime
import traceback
import re

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/my_bets/step_01")
OUTPUT_DIR = Path("docs/win/my_bets/step_02")

ERROR_DIR = Path("docs/win/errors/01_raw")
ERROR_LOG = ERROR_DIR / "my_bets_clean_02.txt"

MAP_DIR = Path("mappings")
NO_MAP_DIR = Path("mappings/need_map")
NO_MAP_PATH = NO_MAP_DIR / "no_map.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)
NO_MAP_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONSTANTS
# =========================

COLUMNS_TO_DELETE = [
    "juice_bet_id",
    "sportsbook",
    "number_of_legs",
    "bet_leg_id",
    "long_description_of_leg",
    "event_start_date",
    "event_name",
]

LEAGUE_PREFIX_MAP = {
    "NBA": "nba_",
    "CBB": "ncaab_",
}

LEG_TYPE_SUFFIX_MAP = {
    "Moneyline": "moneyline",
    "GameOu": "totals",
    "Spread": "spreads",
}

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
    if pd.isna(lg):
        return ""
    return norm(str(lg).split("_")[0])

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

def normalize_value(val, lg, team_map, canonical_sets, unmapped):
    if pd.isna(val):
        return val

    lg = base_league(lg)
    v = norm(val)

    if v in canonical_sets.get(lg, set()):
        return v

    if v in team_map.get(lg, {}):
        return team_map[lg][v]

    unmapped.add((v, lg))
    return v

def build_league_value(leg_league, leg_type):
    prefix = LEAGUE_PREFIX_MAP.get(str(leg_league).strip(), "")
    suffix = LEG_TYPE_SUFFIX_MAP.get(str(leg_type).strip(), "")
    if prefix and suffix:
        return f"{prefix}{suffix}"
    return ""

def extract_teams_from_description(description):
    try:
        if pd.isna(description):
            return "", ""

        main_part = str(description).split(" - ")[0]

        if " @ " in main_part:
            away, home = main_part.split(" @ ", 1)
            return away.strip(), home.strip()

        return "", ""
    except Exception:
        return "", ""

# =========================
# MAIN
# =========================

def process_files():

    summary = []
    summary.append(f"=== MY_BETS_CLEAN_02 RUN @ {datetime.utcnow().isoformat()}Z ===")

    team_map, canonical_sets = load_team_maps()
    unmapped = set()

    input_files = glob.glob(str(INPUT_DIR / "*.csv"))

    files_processed = 0
    rows_processed = 0

    for file_path in input_files:
        try:
            df = pd.read_csv(file_path)

            # =========================
            # DELETE COLUMNS
            # =========================
            for col in COLUMNS_TO_DELETE:
                if col in df.columns:
                    df = df.drop(columns=[col])

            # =========================
            # CREATE LEAGUE COLUMN
            # =========================
            if "leg_league" in df.columns and "leg_type" in df.columns:
                df["league"] = df.apply(
                    lambda row: build_league_value(
                        row["leg_league"],
                        row["leg_type"]
                    ),
                    axis=1
                )
            else:
                df["league"] = ""

            # =========================
            # POPULATE TEAMS
            # =========================
            if "leg_description" in df.columns:
                teams = df["leg_description"].apply(extract_teams_from_description)
                df["away_team"] = teams.apply(lambda x: x[0])
                df["home_team"] = teams.apply(lambda x: x[1])
            else:
                df["away_team"] = ""
                df["home_team"] = ""

            # =========================
            # NORMALIZE TEAMS
            # =========================
            if "league" in df.columns:
                df["away_team"] = [
                    normalize_value(v, lg, team_map, canonical_sets, unmapped)
                    for v, lg in zip(df["away_team"], df["league"])
                ]

                df["home_team"] = [
                    normalize_value(v, lg, team_map, canonical_sets, unmapped)
                    for v, lg in zip(df["home_team"], df["league"])
                ]

            # =========================
            # OUTPUT
            # =========================
            output_path = OUTPUT_DIR / Path(file_path).name
            df.to_csv(output_path, index=False)

            files_processed += 1
            rows_processed += len(df)

        except Exception:
            summary.append(f"ERROR processing {file_path}")
            summary.append(traceback.format_exc())

    # =========================
    # WRITE UNMAPPED
    # =========================
    if unmapped:
        pd.DataFrame(
            sorted(unmapped),
            columns=["team", "league"]
        ).to_csv(NO_MAP_PATH, index=False)

    summary.append(f"Files processed: {files_processed}")
    summary.append(f"Rows processed: {rows_processed}")

    with open(ERROR_LOG, "w") as f:
        f.write("\n".join(summary))


if __name__ == "__main__":
    process_files()
