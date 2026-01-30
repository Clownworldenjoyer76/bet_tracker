# File: scripts/dk_names.py
"""
Normalize DraftKings team names to canonical names using a league-aware mapping.

Input:
  docs/win/manual/cleaned/dk_*.csv

Mapping:
  mappings/team_map.csv
    columns: league, dk_team, canonical_team

Output:
  docs/win/manual/normalized/norm_dk_{league}_{year}_{month}_{day}.csv

Additional output:
  mappings/need_map/no_map.csv
    columns: league, team

Behavior:
- Match on league (normalized)
- Replace team and opponent using dk_team -> canonical_team
- Leave unmapped names unchanged
- Log unmapped teams
- Persist unmapped teams to no_map.csv
- Write output only if changes are detected
"""

from pathlib import Path
import pandas as pd
import re

CLEAN_DIR = Path("docs/win/manual/cleaned")
OUT_DIR = Path("docs/win/manual/normalized")
MAP_PATH = Path("mappings/team_map.csv")

NEED_MAP_DIR = Path("mappings/need_map")
NEED_MAP_DIR.mkdir(parents=True, exist_ok=True)
NO_MAP_PATH = NEED_MAP_DIR / "no_map.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)


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
        lg = row["league"]
        dk = row["dk_team"]
        can = row["canonical_team"]
        if pd.isna(lg) or pd.isna(dk) or pd.isna(can):
            continue
        team_map.setdefault(lg, {})[dk] = can

    return team_map


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


def normalize_file(path: Path, team_map: dict):
    df = pd.read_csv(path, dtype=str)

    # clean_dk_{league}_{year}_{month}_{day}.csv
    parts = path.stem.split("_")
    if len(parts) < 6:
        return

    _, _, league, year, month, day = parts
    league = norm_league(league)

    league_map = team_map.get(league)
    if not league_map:
        print(f"[WARN] No team map for league '{league}' ({path.name})")
        teams = sorted(set(df["team"]) | set(df["opponent"]))
        append_no_map([{"league": league, "team": t} for t in teams])
        return

    # Normalize input strings
    df["league"] = df["league"].apply(norm_league)
    df["team"] = df["team"].apply(norm)
    df["opponent"] = df["opponent"].apply(norm)

    before = df[["team", "opponent"]].copy()

    # Deterministic replacement
    df["team"] = df["team"].apply(lambda x: league_map.get(x, x))
    df["opponent"] = df["opponent"].apply(lambda x: league_map.get(x, x))

    # Identify unmapped teams (missing OR identity-mapped)
    unmapped = sorted(
        t
        for t in set(before["team"]) | set(before["opponent"])
        if t not in league_map or league_map.get(t) == t
    )

    if unmapped:
        print(
            f"[{path.name}] unmapped teams ({league}): "
            f"{len(unmapped)} example={unmapped[:10]}"
        )
        append_no_map([{"league": league, "team": t} for t in unmapped])

    out_path = OUT_DIR / f"norm_dk_{league}_{year}_{month}_{day}.csv"

    # Write only if changed
    if out_path.exists():
        old = pd.read_csv(out_path, dtype=str)
        if old.equals(df):
            return

    df.to_csv(out_path, index=False)
    print(f"[OK] wrote {out_path}")


def main():
    team_map = load_team_map()

    for file in CLEAN_DIR.glob("clean_dk_*.csv"):
        normalize_file(file, team_map)


if __name__ == "__main__":
    main()
