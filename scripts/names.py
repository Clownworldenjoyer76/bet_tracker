# File: scripts/names.py

from pathlib import Path
import pandas as pd

INPUT_DIR = Path("docs/win/manual")
MAP_PATH = Path("mappings/team_map.csv")
NO_MAP_DIR = Path("mappings/need_map")
NO_MAP_PATH = NO_MAP_DIR / "dk_no_map.csv"

NO_MAP_DIR.mkdir(parents=True, exist_ok=True)

def main():
    # Load mapping
    team_map_df = pd.read_csv(MAP_PATH, dtype=str)

    # Build lookup sets
    dk_to_canonical = dict(
        zip(
            team_map_df["dk_team"].astype(str).str.strip(),
            team_map_df["canonical_team"].astype(str).str.strip(),
        )
    )
    canonical_set = set(team_map_df["canonical_team"].astype(str).str.strip())

    unmapped = set()

    for file_path in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(file_path, dtype=str)

        if "league" not in df.columns:
            continue

        # Normalize league → base league only (e.g. ncaab_ml → ncaab)
        base_league = (
            df["league"]
            .astype(str)
            .str.split("_")
            .str[0]
            .iloc[0]
        )

        # Build league-scoped maps
        league_df = team_map_df[team_map_df["league"] == base_league]
        league_dk_to_canonical = dict(
            zip(
                league_df["dk_team"].astype(str).str.strip(),
                league_df["canonical_team"].astype(str).str.strip(),
            )
        )
        league_canonical_set = set(
            league_df["canonical_team"].astype(str).str.strip()
        )

        for col in ("team", "opponent"):
            if col not in df.columns:
                continue

            def replace(val):
                if pd.isna(val):
                    return val

                val = str(val).strip()

                # Already canonical → leave it alone
                if val in league_canonical_set:
                    return val

                # DK alias → replace
                if val in league_dk_to_canonical:
                    return league_dk_to_canonical[val]

                # Truly unmapped
                unmapped.add(val)
                return val

            df[col] = df[col].apply(replace)

        df.to_csv(file_path, index=False)

    if unmapped:
        pd.DataFrame(sorted(unmapped), columns=["team"]).to_csv(
            NO_MAP_PATH, index=False
        )

if __name__ == "__main__":
    main()
