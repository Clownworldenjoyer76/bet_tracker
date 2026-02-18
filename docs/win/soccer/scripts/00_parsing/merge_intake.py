#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/merge_intake.py

import sys
import csv
from pathlib import Path
from datetime import datetime

# =========================
# ARGUMENTS
# =========================
# Expects:
#   1) league (soccer)
#   2) market (mls, epl, etc.)

league = sys.argv[1].strip()
market = sys.argv[2].strip()

# =========================
# PATHS
# =========================

BASE_DIR = Path("docs/win/soccer/00_intake")
SPORTSBOOK_DIR = BASE_DIR / "sportsbook"
PRED_DIR = BASE_DIR / "predictions"

# =========================
# LOAD LATEST FILES
# =========================

def get_latest_file(directory: Path, prefix: str):
    files = sorted(directory.glob(f"{prefix}_*.csv"), key=lambda x: x.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No files found in {directory} with prefix {prefix}")
    return files[-1]

dk_file = get_latest_file(SPORTSBOOK_DIR, f"{market}_dk")
pred_file = get_latest_file(PRED_DIR, f"{market}_pred")

# =========================
# LOAD DK DATA
# =========================

dk_data = {}

with open(dk_file, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = (
            row["league"],
            row["market"],
            row["home_team"],
            row["away_team"],
        )
        dk_data[key] = {
            "home_american": row["dk_home_american"],
            "draw_american": row["dk_draw_american"],
            "away_american": row["dk_away_american"],
        }

# =========================
# MERGE WITH PREDICTIONS
# =========================

merged_rows = []
match_date_for_filename = None

with open(pred_file, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = (
            row["league"],
            row["market"],
            row["home_team"],
            row["away_team"],
        )

        if key not in dk_data:
            continue  # skip unmatched rows

        if not match_date_for_filename:
            match_date_for_filename = row["match_date"]

        game_id = f"{row['league']}_{row['market']}_{row['match_date']}_{row['home_team']}_{row['away_team']}"

        merged_rows.append([
            row["league"],
            row["market"],
            row["match_date"],
            row["match_time"],
            row["home_team"],
            row["away_team"],
            row["home_prob"],
            row["draw_prob"],
            row["away_prob"],
            dk_data[key]["home_american"],
            dk_data[key]["draw_american"],
            dk_data[key]["away_american"],
            game_id,
        ])

# =========================
# OUTPUT
# =========================

if not merged_rows:
    raise ValueError("No matching rows found to merge")

output_file = BASE_DIR / f"{match_date_for_filename}_{league}_{market}.csv"

with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "league",
        "market",
        "match_date",
        "match_time",
        "home_team",
        "away_team",
        "home_prob",
        "draw_prob",
        "away_prob",
        "home_american",
        "draw_american",
        "away_american",
        "game_id",
    ])
    writer.writerows(merged_rows)

print(f"Wrote {output_file} ({len(merged_rows)} rows)")
