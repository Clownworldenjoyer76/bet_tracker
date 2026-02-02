#!/usr/bin/env python3

import csv
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
INPUT_CLEANED_DIR = BASE_DIR / "docs/win/cleaned"
INPUT_NORM_DIR = BASE_DIR / "docs/win/manual/normalized"
# The sub-folder
OUTPUT_DIR = INPUT_CLEANED_DIR / "cleaned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_fix():
    # Only process CSVs directly in INPUT_CLEANED_DIR
    # This prevents it from looking into the 'cleaned/cleaned' subfolder
    for file_path in INPUT_CLEANED_DIR.iterdir():
        if not file_path.name.endswith(".csv") or not file_path.name.startswith("clean_"):
            continue
            
        match = re.search(r"clean_([a-z]+)_(\d{4})[-_](\d{2})[-_](\d{2})", file_path.name)
        if not match: 
            continue
        
        league, yyyy, mm, dd = match.groups()
        date_str = f"{yyyy}_{mm}_{dd}"
        norm_filename = f"norm_dk_{league}_totals_{date_str}.csv"
        norm_path = INPUT_NORM_DIR / norm_filename
        
        if not norm_path.exists():
            print(f"File Not Found: {norm_path}")
            continue

        team_lookup = {}
        with open(norm_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team = str(row.get("team", "")).strip().lower()
                side = str(row.get("side", "")).strip().upper()
                if team not in team_lookup:
                    team_lookup[team] = {"total": row.get("total", ""), "OVER": {}, "UNDER": {}}
                if side in ["OVER", "UNDER"]:
                    team_lookup[team][side] = row

        updated_rows = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                away_team = str(row.get("away_team", "")).strip().lower()
                dk = team_lookup.get(away_team)
                if dk:
                    row["total"] = dk.get("total", "")
                    row["over_total_odds"] = dk["OVER"].get("odds", "")
                    row["under_total_odds"] = dk["UNDER"].get("odds", "")
                    row["over_handle_pct"] = dk["OVER"].get("handle_pct", "")
                    row["under_handle_pct"] = dk["UNDER"].get("handle_pct", "")
                    row["over_bets_pct"] = dk["OVER"].get("bets_pct", "")
                    row["under_bets_pct"] = dk["UNDER"].get("bets_pct", "")
                updated_rows.append(row)

        out_path = OUTPUT_DIR / file_path.name
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(updated_rows)
        print(f"Saved: {out_path}")

if __name__ == "__main__":
    run_fix()
