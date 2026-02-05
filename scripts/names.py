# scripts/names.py

import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/manual")
MAP_PATH = Path("mappings/team_map.csv")
NEED_MAP_DIR = Path("mappings/need_map")
NEED_MAP_DIR.mkdir(parents=True, exist_ok=True)
NO_MAP_PATH = NEED_MAP_DIR / "dk_no_map.csv"

def main():
    team_map_df = pd.read_csv(MAP_PATH, dtype=str)
    team_map = dict(zip(team_map_df["dk_team"], team_map_df["canonical_team"]))

    no_map_rows = []

    for csv_path in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(csv_path, dtype=str)

        for col in ("team", "opponent"):
            if col not in df.columns:
                continue

            for idx, val in df[col].items():
                if pd.isna(val):
                    continue

                if val in team_map:
                    df.at[idx, col] = team_map[val]
                else:
                    no_map_rows.append({"team": val})

        df.to_csv(csv_path, index=False)

    if no_map_rows:
        no_map_df = pd.DataFrame(no_map_rows).drop_duplicates()
        if NO_MAP_PATH.exists():
            existing = pd.read_csv(NO_MAP_PATH, dtype=str)
            no_map_df = pd.concat([existing, no_map_df], ignore_index=True).drop_duplicates()
        no_map_df.to_csv(NO_MAP_PATH, index=False)

if __name__ == "__main__":
    main()
