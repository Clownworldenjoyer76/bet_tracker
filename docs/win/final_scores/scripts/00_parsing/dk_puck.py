#!/usr/bin/env python3

import sys
import pandas as pd
from pathlib import Path

# =========================
# ARGUMENT
# =========================
# Usage:
# python add_dk_lines.py 2026_03_02

if len(sys.argv) != 2:
    print("Usage: python add_dk_lines.py YYYY_MM_DD")
    sys.exit(1)

date = sys.argv[1]

# =========================
# PATHS
# =========================

SPORTSBOOK_FILE = Path(f"docs/win/hockey/00_intake/sportsbook/hockey_{date}.csv")
FINAL_FILE = Path(f"docs/win/final_scores/{date}_final_scores_NHL.csv")

# =========================
# LOAD FILES
# =========================

if not SPORTSBOOK_FILE.exists():
    raise FileNotFoundError(f"Sportsbook file not found: {SPORTSBOOK_FILE}")

if not FINAL_FILE.exists():
    raise FileNotFoundError(f"Final scores file not found: {FINAL_FILE}")

sportsbook_df = pd.read_csv(SPORTSBOOK_FILE)
final_df = pd.read_csv(FINAL_FILE)

# =========================
# RENAME SPORTSBOOK COLUMNS
# =========================

sportsbook_df = sportsbook_df.rename(columns={
    "away_puck_line": "dk_away_puck_line",
    "home_puck_line": "dk_home_puck_line",
    "total": "dk_total"
})

# =========================
# REQUIRED MERGE KEY
# =========================
# Assumes these exist in BOTH files:
# game_date, away_team, home_team

merge_cols = ["game_date", "away_team", "home_team"]

for col in merge_cols:
    if col not in sportsbook_df.columns:
        raise KeyError(f"{col} missing from sportsbook file")
    if col not in final_df.columns:
        raise KeyError(f"{col} missing from final scores file")

# =========================
# SELECT ONLY NEEDED COLUMNS
# =========================

sportsbook_subset = sportsbook_df[
    merge_cols + [
        "dk_away_puck_line",
        "dk_home_puck_line",
        "dk_total"
    ]
]

# =========================
# MERGE (LEFT JOIN)
# =========================

merged_df = final_df.merge(
    sportsbook_subset,
    on=merge_cols,
    how="left"
)

# =========================
# SAVE BACK TO SAME FILE
# =========================

merged_df.to_csv(FINAL_FILE, index=False)

print(f"DK lines added successfully for {date}")
