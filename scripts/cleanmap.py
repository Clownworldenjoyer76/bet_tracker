# scripts/cleanmap.py

#!/usr/bin/env python3

from pathlib import Path
import pandas as pd

MAP_DIR = Path("mappings")

def clean_string(s):
    if pd.isna(s):
        return s
    s = str(s).strip()
    s = s.replace("–", " ")
    s = s.replace("—", " ")
    s = " ".join(s.split())
    return s

def process_file(path: Path):
    print(f"Processing: {path.name}")

    df = pd.read_csv(path, dtype=str)

    if not {"league", "alias", "canonical_team"}.issubset(df.columns):
        print(f"Skipping {path.name} — missing required columns")
        return

    # Clean fields
    df["alias"] = df["alias"].apply(clean_string)
    df["canonical_team"] = df["canonical_team"].apply(clean_string)

    # Build full set of all names
    all_names = pd.concat([df["alias"], df["canonical_team"]]).dropna().unique()

    canonical_map = {}

    for name in all_names:
        # Find all rows connected to this name
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

    # Rebuild normalized rows
    league_value = df["league"].iloc[0]

    new_rows = []
    for alias in sorted(canonical_map.keys()):
        canonical = canonical_map[alias]
        new_rows.append({
            "league": league_value,
            "alias": alias,
            "canonical_team": canonical
        })

    new_df = pd.DataFrame(new_rows).drop_duplicates()

    # Overwrite original file
    new_df.to_csv(path, index=False)

    print(f"Normalized and overwritten: {path.name}\n")

def main():
    files = sorted(MAP_DIR.glob("team_map_ncaab_*.csv"))

    if not files:
        print("No matching NCAAB mapping files found.")
        return

    for path in files:
        process_file(path)

    print("All NCAAB mapping files normalized.")

if __name__ == "__main__":
    main()
