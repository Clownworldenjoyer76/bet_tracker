# File: scripts/dk_names.py
"""
Normalize DraftKings team names to canonical names using a league-aware mapping.

Input:
  docs/win/manual/cleaned/clean_dk_*.csv

Mapping:
  mappings/team_map.csv
    columns: league, dk_team, canonical_team

Output:
  docs/win/manual/normalized/norm_dk_{league}_{year}_{month}_{day}.csv

Behavior:
- Match on league
- Replace team and opponent using dk_team -> canonical_team
- Leave unmapped names unchanged
- Write output only if changes are detected
"""

from pathlib import Path
import pandas as pd

CLEAN_DIR = Path("docs/win/manual/cleaned")
OUT_DIR = Path("docs/win/manual/normalized")
MAP_PATH = Path("mappings/team_map.csv")

OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_team_map() -> dict:
    df = pd.read_csv(MAP_PATH)

    # Build {league: {dk_team: canonical_team}}
    team_map = {}
    for _, row in df.iterrows():
        team_map.setdefault(row["league"], {})[row["dk_team"]] = row["canonical_team"]

    return team_map


def normalize_file(path: Path, team_map: dict):
    df = pd.read_csv(path)

    parts = path.stem.split("_")
    if len(parts) < 6:
        return

    _, _, league, year, month, day = parts

    league_map = team_map.get(league)
    if not league_map:
        return

    df["team"] = df["team"].map(lambda x: league_map.get(x, x))
    df["opponent"] = df["opponent"].map(lambda x: league_map.get(x, x))

    out_path = OUT_DIR / f"norm_dk_{league}_{year}_{month}_{day}.csv"

    if out_path.exists():
        old = pd.read_csv(out_path)
        if old.equals(df):
            return

    df.to_csv(out_path, index=False)


def main():
    team_map = load_team_map()

    for file in CLEAN_DIR.glob("clean_dk_*.csv"):
        normalize_file(file, team_map)


if __name__ == "__main__":
    main()
