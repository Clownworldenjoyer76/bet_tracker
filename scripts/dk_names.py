# File: scripts/dk_names.py

from pathlib import Path
import pandas as pd
import re

############################################
# PATHS
############################################

# DK manual paths
CLEAN_DIR = Path("docs/win/manual/cleaned")
OUT_DIR = Path("docs/win/manual/normalized")

# Dump paths (canonicalized IN PLACE)
DUMP_DIR = Path("docs/win/dump/csvs/cleaned")

MAP_PATH = Path("mappings/team_map.csv")

NEED_MAP_DIR = Path("mappings/need_map")
NEED_MAP_DIR.mkdir(parents=True, exist_ok=True)
NO_MAP_PATH = NEED_MAP_DIR / "no_map.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

############################################
# NORMALIZATION HELPERS
############################################

def norm(s: str) -> str:
    if pd.isna(s):
        return s
    s = str(s).replace("\u00A0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def norm_league(s: str) -> str:
    if pd.isna(s):
        return s
    return norm(s).lower()

############################################
# TEAM MAP
############################################

def load_team_map() -> dict:
    df = pd.read_csv(MAP_PATH, dtype=str)

    df["league"] = df["league"].apply(norm_league)
    df["dk_team"] = df["dk_team"].apply(norm)
    df["canonical_team"] = df["canonical_team"].apply(norm)

    team_map: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        lg = row["league"]
        dk = row["dk_team"]
        can = row["canonical_team"]
        if pd.isna(lg) or pd.isna(dk) or pd.isna(can):
            continue
        team_map.setdefault(lg, {})[dk] = can

    return team_map

############################################
# UNMAPPED LOGGING
############################################

def append_no_map(rows: list[dict]):
    if not rows:
        return

    new_df = pd.DataFrame(rows)

    if NO_MAP_PATH.exists():
        try:
            old_df = pd.read_csv(NO_MAP_PATH, dtype=str)
            combined = pd.concat([old_df, new_df], ignore_index=True)
        except pd.errors.EmptyDataError:
            combined = new_df
    else:
        combined = new_df

    combined = combined.drop_duplicates()
    combined.to_csv(NO_MAP_PATH, index=False)

############################################
# DK MANUAL NORMALIZATION
############################################

def parse_dk_filename(path: Path):
    parts = path.stem.split("_")
    if len(parts) < 6 or parts[0] != "dk":
        raise ValueError(f"Invalid filename format: {path.name}")

    year, month, day = parts[-3:]
    league = parts[1]
    market = "_".join(parts[2:-3])

    return norm_league(league), market, year, month, day


def normalize_dk_file(path: Path, team_map: dict):
    league, market, year, month, day = parse_dk_filename(path)

    df = pd.read_csv(path, dtype=str)

    league_map = team_map.get(league)
    if not league_map:
        teams = sorted(set(df["team"]) | set(df["opponent"]))
        append_no_map([{"league": league, "team": t} for t in teams])
        return

    df["league"] = df["league"].apply(norm_league)
    df["team"] = df["team"].apply(norm)
    df["opponent"] = df["opponent"].apply(norm)

    before = set(df["team"]) | set(df["opponent"])

    df["team"] = df["team"].map(lambda x: league_map.get(x, x))
    df["opponent"] = df["opponent"].map(lambda x: league_map.get(x, x))

    unmapped = sorted(t for t in before if t not in league_map)
    if unmapped:
        append_no_map([{"league": league, "team": t} for t in unmapped])

    out_path = OUT_DIR / f"norm_dk_{league}_{market}_{year}_{month}_{day}.csv"
    df.to_csv(out_path, index=False)

############################################
# DUMP NORMALIZATION (IN PLACE)
############################################

def normalize_dump_file(path: Path, team_map: dict):
    # filename: league_YYYY_MM_DD.csv
    league = norm_league(path.stem.split("_")[0])

    df = pd.read_csv(path, dtype=str)
    league_map = team_map.get(league)
    if not league_map:
        return

    df["home_team"] = df["home_team"].apply(norm)
    df["away_team"] = df["away_team"].apply(norm)

    before = set(df["home_team"]) | set(df["away_team"])

    df["home_team"] = df["home_team"].map(lambda x: league_map.get(x, x))
    df["away_team"] = df["away_team"].map(lambda x: league_map.get(x, x))

    unmapped = sorted(t for t in before if t not in league_map)
    if unmapped:
        append_no_map([{"league": league, "team": t} for t in unmapped])

    df.to_csv(path, index=False)

############################################
# MAIN
############################################

def main():
    team_map = load_team_map()

    # 1️⃣ Normalize DK manual files
    for file in CLEAN_DIR.glob("dk_*.csv"):
        normalize_dk_file(file, team_map)

    # 2️⃣ Normalize dump cleaned files (authoritative)
    for file in DUMP_DIR.glob("*.csv"):
        normalize_dump_file(file, team_map)

if __name__ == "__main__":
    main()
