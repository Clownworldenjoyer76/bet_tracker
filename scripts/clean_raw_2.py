#!/usr/bin/env python3

import csv
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
INPUT_CLEANED_DIR = BASE_DIR / "docs/win/cleaned"
INPUT_NORM_DIR = BASE_DIR / "docs/win/manual/normalized"
OUTPUT_DIR = BASE_DIR / "docs/win/cleaned/final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_fix():
    # Loop through cleaned files (e.g., clean_nba_2026-01-28.csv)
    for file_path in INPUT_CLEANED_DIR.glob("clean_*.csv"):
        if "final" in file_path.parts: continue
        
        # Regex to pull league and date parts
        match = re.search(r"clean_([a-z]+)_(\d{4})-(\d{2})-(\d{2})", file_path.name)
        if not match: continue
        
        league, yyyy, mm, dd = match.groups()
        date_str = f"{yyyy}_{mm}_{dd}"
        
        # Target the TOTALS market file specifically
        norm_filename = f"norm_dk_{league}_totals_{date_str}.csv"
        norm_path = INPUT_NORM_DIR / norm_filename
        
        if not norm_path.exists():
            print(f"File Not Found: {norm_path}")
            continue

        # 1. Map Normalized Totals Data
        dk_lookup = {}
        with open(norm_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gid = row.get("game_id")
                side = str(row.get("side", "")).strip().upper()
                
                if gid not in dk_lookup:
                    dk_lookup[gid] = {"total": row.get("total", ""), "OVER": {}, "UNDER": {}}
                
                if side in ["OVER", "UNDER"]:
                    dk_lookup[gid][side] = row

        # 2. Update Cleaned File Rows
        updated_rows = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                gid = row.get("game_id")
                dk = dk_lookup.get(gid)
                
                if dk:
                    row["total"] = dk.get("total", "")
                    row["over_total_odds"] = dk["OVER"].get("odds", "")
                    row["under_total_odds"] = dk["UNDER"].get("odds", "")
                    row["over_handle_pct"] = dk["OVER"].get("handle_pct", "")
                    row["under_handle_pct"] = dk["UNDER"].get("handle_pct", "")
                    row["over_bets_pct"] = dk["OVER"].get("bets_pct", "")
                    row["under_bets_pct"] = dk["UNDER"].get("bets_pct", "")
                
                updated_rows.append(row)

        # 3. Write to Final
        out_path = OUTPUT_DIR / file_path.name
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(updated_rows)
        print(f"Processed: {out_path.name}")

if __name__ == "__main__":
    run_fix()
