#!/usr/bin/env python3

from pathlib import Path
import pandas as pd

MAP_PATH = Path("mappings/team_map_ncaab.csv")

def clean_string(s):
    if pd.isna(s):
        return s
    s = str(s).strip()
    s = s.replace("–", " ")
    s = s.replace("—", " ")
    s = " ".join(s.split())
    return s

def main():
    if not MAP_PATH.exists():
        print("team_map_ncaab.csv not found.")
        return

    df = pd.read_csv(MAP_PATH, dtype=str)

    if not {"league", "alias", "canonical_team"}.issubset(df.columns):
        print("Required columns missing.")
        return

    df["alias"] = df["alias"].apply(clean_string)
    df["canonical_team"] = df["canonical_team"].apply(clean_string)

    # Build full set of names
    all_names = pd.concat([df["alias"], df["canonical_team"]]).dropna().unique()

    canonical_map = {}

    for name in all_names:
        matches = df[
            (df["alias"] == name) |
            (df["canonical_team"] == name)
        ]

        if matches.empty:
            continue

        names = set(matches["alias"]).union(set(matches["canonical_team"]))

        # Choose longest string as canonical
        canonical = max(names, key=len)

        for n in names:
            canonical_map[n] = canonical

    league_value = df["league"].iloc[0]

    new_rows = []
    for alias in sorted(canonical_map.keys()):
        new_rows.append({
            "league": league_value,
            "alias": alias,
            "canonical_team": canonical_map[alias]
        })

    new_df = pd.DataFrame(new_rows).drop_duplicates()

    # Overwrite original file
    new_df.to_csv(MAP_PATH, index=False)

    print("Normalized and overwritten team_map_ncaab.csv")

if __name__ == "__main__":
    main()
