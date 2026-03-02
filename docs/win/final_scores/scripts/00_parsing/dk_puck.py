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
    sys.exit(0)

date = sys.argv[1]

# =========================
# PATHS
# =========================

SPORTSBOOK_FILE = Path(f"docs/win/hockey/00_intake/sportsbook/hockey_{date}.csv")
FINAL_FILE = Path(f"docs/win/final_scores/{date}_final_scores_NHL.csv")

# =========================
# SILENT FAIL CONDITIONS
# =========================

if not FINAL_FILE.exists():
    sys.exit(0)

if not SPORTSBOOK_FILE.exists():
    sys.exit(0)

# =========================
# LOAD FILES
# =========================

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

merge_cols = ["game_date", "away_team", "home_team"]

# If merge columns missing, fail silently
for col in merge_cols:
    if col not in sportsbook_df.columns:
        sys.exit(0)
    if col not in final_df.columns:
        sys.exit(0)

# =========================
# SELECT NEEDED COLUMNS
# =========================

sportsbook_subset = sportsbook_df[
    merge_cols + [
        "dk_away_puck_line",
        "dk_home_puck_line",
        "dk_total"
    ]
]

# =========================
# MERGE
# =========================

merged_df = final_df.merge(
    sportsbook_subset,
    on=merge_cols,
    how="left"
)

# =========================
# SAVE
# =========================

merged_df.to_csv(FINAL_FILE, index=False)
