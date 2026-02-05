#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import re

INPUT_DIR = Path("docs/win/manual")
MAP_PATH = Path("mappings/team_map.csv")
NEED_MAP_DIR = Path("mappings/need_map")
NEED_MAP_DIR.mkdir(parents=True, exist_ok=True)
NO_MAP_PATH = NEED_MAP_DIR / "dk_no_map.csv"


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


def load_team_map() -> dict:
    df = pd.read_csv(MAP_PATH, dtype=str)
    df["league"] = df["league"].apply(norm_league)
    df["dk_team"] = df["dk_team"].apply(norm)
    df["canonical_team"] = df["canonical_team"].apply(norm)

    team_map: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        league = row["league"]
        dk_team = row["dk_team"]
        canonical = row["canonical_team"]
        if pd.isna(league) or pd.isna(dk_team) or pd.isna(canonical):
            continue
        team_map.setdefault(league, {})[dk_team] = canonical

    return team_map


def main():
    team_map = load_team_map()
    no_map_rows = []

    for path in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(path, dtype=str)

        if "team" not in df.columns or "opponent" not in df.columns or "league" not in df.columns:
            continue

        df["league"] = df["league"].apply(norm_league)
        df["team"] = df["team"].apply(norm)
        df["opponent"] = df["opponent"].apply(norm)

        for idx, row in df.iterrows():
            league = row["league"]
            league_map = team_map.get(league, {})

            team = row["team"]
            opp = row["opponent"]

            if team in league_map:
                df.at[idx, "team"] = league_map[team]
            else:
                no_map_rows.append({
                    "league": league,
                    "team": team,
                    "file": path.name,
                    "column": "team",
                })

            if opp in league_map:
                df.at[idx, "opponent"] = league_map[opp]
            else:
                no_map_rows.append({
                    "league": league,
                    "team": opp,
                    "file": path.name,
                    "column": "opponent",
                })

        df.to_csv(path, index=False)

    if no_map_rows:
        new_df = pd.DataFrame(no_map_rows).drop_duplicates()
        if NO_MAP_PATH.exists():
            old_df = pd.read_csv(NO_MAP_PATH, dtype=str)
            new_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates()
        new_df.to_csv(NO_MAP_PATH, index=False)


if __name__ == "__main__":
    main()
