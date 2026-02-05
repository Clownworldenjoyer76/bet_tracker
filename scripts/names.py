# File: scripts/names.py

from pathlib import Path
import pandas as pd

INPUT_DIR = Path("docs/win/manual")
MAP_PATH = Path("mappings/team_map.csv")
NO_MAP_DIR = Path("mappings/need_map")
NO_MAP_PATH = NO_MAP_DIR / "dk_no_map.csv"

NO_MAP_DIR.mkdir(parents=True, exist_ok=True)

def main():
    team_map_df = pd.read_csv(MAP_PATH, dtype=str)
    team_map = dict(
        zip(team_map_df["dk_team"].astype(str), team_map_df["canonical_team"].astype(str))
    )

    unmapped = set()

    for file_path in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(file_path, dtype=str)

        for col in ["team", "opponent"]:
            if col not in df.columns:
                continue

            def replace_team(val):
                if pd.isna(val):
                    return val
                if val in team_map:
                    return team_map[val]
                unmapped.add(val)
                return val

            df[col] = df[col].apply(replace_team)

        df.to_csv(file_path, index=False)

    if unmapped:
        pd.DataFrame(sorted(unmapped), columns=["team"]).to_csv(NO_MAP_PATH, index=False)

if __name__ == "__main__":
    main()
