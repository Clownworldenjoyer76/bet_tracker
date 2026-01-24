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
- Match on league (normalized)
- Replace team and opponent using dk_team -> canonical_team (normalized)
- Leave unmapped names unchanged
- Write output only if changes are detected
"""

from pathlib import Path
import pandas as pd
import re

CLEAN_DIR = Path("docs/win/manual/cleaned")
OUT_DIR = Path("docs/win/manual/normalized")
MAP_PATH = Path("mappings/team_map.csv")

OUT_DIR.mkdir(parents=True, exist_ok=True)


def norm(s: str) -> str:
    """Normalize strings for reliable matching (trim, collapse spaces, fix NBSP, lower for league)."""
    if pd.isna(s):
        return s
    s = str(s).replace("\u00A0", " ").strip()          # NBSP -> space, trim
    s = re.sub(r"\s+", " ", s)                         # collapse whitespace
    return s


def norm_league(s: str) -> str:
    return norm(s).lower() if not pd.isna(s) else s


def load_team_map() -> dict:
    df = pd.read_csv(MAP_PATH, dtype=str)

    # Normalize mapping columns
    df["league"] = df["league"].apply(norm_league)
    df["dk_team"] = df["dk_team"].apply(norm)
    df["canonical_team"] = df["canonical_team"].apply(norm)

    # Build {league: {dk_team: canonical_team}}
    team_map: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        lg = row["league"]
        dk = row["dk_team"]
        can = row["canonical_team"]
        if pd.isna(lg) or pd.isna(dk) or pd.isna(can):
            continue
        team_map.setdefault(lg, {})[dk] = can

    return team_map


def normalize_file(path: Path, team_map: dict):
    df = pd.read_csv(path, dtype=str)

    parts = path.stem.split("_")
    # clean_dk_{league}_{year}_{month}_{day}.csv -> 6 parts
    if len(parts) < 6:
        return

    _, _, league, year, month, day = parts
    league = norm_league(league)

    league_map = team_map.get(league)
    if not league_map:
        return

    # Normalize input strings before replacement
    df["league"] = df["league"].apply(norm_league)
    df["team"] = df["team"].apply(norm)
    df["opponent"] = df["opponent"].apply(norm)

    before = df[["team", "opponent"]].copy()

    # Replace using the league-specific dict
    df["team"] = df["team"].replace(league_map)
    df["opponent"] = df["opponent"].replace(league_map)

    # Optional: log unmapped teams for this file (helps you finish team_map.csv)
    unmapped = sorted(set(before["team"]) | set(before["opponent"]) - set(league_map.keys()))
    if unmapped:
        print(f"[{path.name}] unmapped ({league}) count={len(unmapped)} example={unmapped[:10]}")

    out_path = OUT_DIR / f"norm_dk_{league}_{year}_{month}_{day}.csv"

    # Only write if changed
    if out_path.exists():
        old = pd.read_csv(out_path, dtype=str)
        if old.equals(df):
            return

    df.to_csv(out_path, index=False)


def main():
    team_map = load_team_map()
    for file in CLEAN_DIR.glob("clean_dk_*.csv"):
        normalize_file(file, team_map)


if __name__ == "__main__":
    main()
