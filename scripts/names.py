# File: scripts/names.py

from pathlib import Path
import pandas as pd

INPUT_DIR = Path("docs/win/manual")
MAP_PATH = Path("mappings/team_map.csv")
NO_MAP_DIR = Path("mappings/need_map")
NO_MAP_PATH = NO_MAP_DIR / "dk_no_map.csv"

NO_MAP_DIR.mkdir(parents=True, exist_ok=True)

def main():
    map_df = pd.read_csv(MAP_PATH, dtype=str)

    # Build lookup structures
    # team_map: league -> {dk_team: canonical_team}
    # canonical_sets: league -> set(canonical_team)
    team_map = {}
    canonical_sets = {}

    for _, row in map_df.iterrows():
        lg = row["league"].strip()
        dk = row["dk_team"].strip()
        can = row["canonical_team"].strip()

        team_map.setdefault(lg, {})[dk] = can
        canonical_sets.setdefault(lg, set()).add(can)

    unmapped = set()

    for file_path in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(file_path, dtype=str)

        if "league" not in df.columns:
            continue

        for col in ("team", "opponent"):
            if col not in df.columns:
                continue

            def replace(val, lg):
                if pd.isna(val):
                    return val

                base_lg = lg.split("_")[0]

                # already canonical
                if val in canonical_sets.get(base_lg, set()):
                    return val

                # dk_team -> canonical_team
                if val in team_map.get(base_lg, {}):
                    return team_map[base_lg][val]

                # no match
                unmapped.add(val)
                return val

            df[col] = [
                replace(v, lg) for v, lg in zip(df[col], df["league"])
            ]

        df.to_csv(file_path, index=False)

    if unmapped:
        pd.DataFrame(sorted(unmapped), columns=["team"]).to_csv(
            NO_MAP_PATH, index=False
        )

if __name__ == "__main__":
    main()
