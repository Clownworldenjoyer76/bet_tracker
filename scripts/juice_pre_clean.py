#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import sys

# =========================
# CONFIG
# =========================

INPUT_PATTERNS = [
    "docs/win/nba/moneyline/*.csv",
    "docs/win/nba/spreads/*.csv",
    "docs/win/nba/totals/*.csv",
    "docs/win/ncaab/moneyline/*.csv",
    "docs/win/ncaab/spreads/*.csv",
    "docs/win/ncaab/totals/*.csv",
]

EXPLICIT_ODDS_COLUMNS = {
    "away_odds",
    "home_odds",
    "over_odds",
    "under_odds",
    "away_spread_acceptable_american_odds",
    "home_spread_acceptable_american_odds",
    "over_acceptable_american_odds",
    "under_acceptable_american_odds",
    "away_ml_fair_american_odds",
    "away_ml_acceptable_american_odds",
    "home_ml_fair_american_odds",
    "home_ml_acceptable_american_odds",
}

# =========================
# HELPERS
# =========================

def is_odds_column(col: str) -> bool:
    return (
        "american_odds" in col
        or col in EXPLICIT_ODDS_COLUMNS
    )

def normalize_american(val, file, col):
    if pd.isna(val):
        return val

    if isinstance(val, (int, float)):
        return int(val)

    s = str(val).strip()

    if s.startswith("+"):
        s = s[1:]

    if s.startswith("-"):
        sign = -1
        s = s[1:]
    else:
        sign = 1

    if not s.isdigit():
        raise ValueError(
            f"Non-numeric American odds '{val}' "
            f"in {file} column '{col}'"
        )

    return sign * int(s)

# =========================
# MAIN
# =========================

def main():
    files = []
    for pattern in INPUT_PATTERNS:
        files.extend(glob.glob(pattern))

    if not files:
        print("juice_pre_clean: no input files found")
        return

    total_files = 0
    total_columns = 0
    total_values = 0

    for file in files:
        path = Path(file)
        df = pd.read_csv(path)

        odds_cols = [c for c in df.columns if is_odds_column(c)]
        if not odds_cols:
            continue

        total_files += 1
        total_columns += len(odds_cols)

        for col in odds_cols:
            df[col] = df[col].apply(
                lambda v: normalize_american(v, file, col)
            )
            total_values += df[col].notna().sum()

        df.to_csv(path, index=False)
        print(f"Normalized odds in {path}")

    print("\nJUICE PRE-CLEAN SUMMARY")
    print("=======================")
    print(f"Files processed: {total_files}")
    print(f"Columns normalized: {total_columns}")
    print(f"Values normalized: {total_values}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"juice_pre_clean FAILED: {e}", file=sys.stderr)
        sys.exit(1)
