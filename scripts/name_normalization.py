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
    """
    Loads mappings/team_map_{league}.csv
    Returns:
        team_map[league][alias] -> canonical
        canonical_sets[league] -> set(canonical)
    """
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

# =========================
# MAIN
# =========================

def main():
    try:
        team_map, canonical_sets = load_team_maps()
        unmapped = set()

        # ==================================================
        # MANUAL FILES (DK)
        # ==================================================

        for file_path in MANUAL_DIR.glob("*.csv"):
            df = pd.read_csv(file_path, dtype=str)

            if "league" not in df.columns:
                continue

            for col in ("team", "opponent"):
                if col not in df.columns:
                    continue

                df[col] = [
                    normalize_value(v, lg, team_map, canonical_sets, unmapped)
                    for v, lg in zip(df[col], df["league"])
                ]

            df.to_csv(file_path, index=False)

        # ==================================================
        # DUMP FILES
        # ==================================================

        for file_path in DUMP_DIR.glob("*.csv"):
            parts = file_path.stem.split("_")
            if len(parts) < 2:
                continue

            lg = parts[0]
            df = pd.read_csv(file_path, dtype=str)

            for col in ("home_team", "away_team"):
                if col not in df.columns:
                    continue

                df[col] = df[col].apply(
                    lambda v: normalize_value(
                        v, lg, team_map, canonical_sets, unmapped
                    )
                )

            df.to_csv(file_path, index=False)

        # ==================================================
        # WRITE UNMAPPED
        # ==================================================

        if unmapped:
            pd.DataFrame(
                sorted(unmapped),
                columns=["team", "league"]
            ).to_csv(NO_MAP_PATH, index=False)

    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
            f.write("\n" + "-" * 80 + "\n")

# =========================

if __name__ == "__main__":
    main()
