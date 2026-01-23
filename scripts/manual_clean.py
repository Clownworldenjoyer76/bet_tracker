# File: scripts/manual_clean.py
"""
Skeleton script for manually cleaning DraftKings CSV dumps.

Input:
  docs/win/manual/*.csv

Output:
  docs/win/manual/cleaned/clean_dk_{league}_{year}_{month}_{day}.csv

Behavior:
- Normalize date and time columns
- Rename team/opponent columns
- Normalize odds minus sign
- Convert handle/bets percentages to numeric decimals
- Add market column
- If output exists, update only if changes are detected
- If no changes, exit silently
"""

from pathlib import Path
import pandas as pd
from datetime import datetime

INPUT_DIR = Path("docs/win/manual")
OUTPUT_DIR = INPUT_DIR / "cleaned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_date(date_str: str, year: int) -> str:
    """Convert M/D -> MM/DD/YYYY"""
    month, day = date_str.split("/")
    return f"{int(month):02d}/{int(day):02d}/{year}"


def normalize_time(time_str: str) -> str:
    """Convert 07:10PM -> 07:10 PM"""
    return time_str[:-2] + " " + time_str[-2:]


def clean_file(path: Path):
    df = pd.read_csv(path)

    # Infer metadata from filename: dk_{league}_{year}_{month}_{day}.csv
    parts = path.stem.split("_")
    if len(parts) < 5:
        return

    _, league, year, month, day = parts
    year = int(year)

    # Date / time normalization
    df["date"] = df["date"].apply(lambda x: normalize_date(x, year))
    df["time"] = df["time"].apply(normalize_time)

    # Rename columns
    df = df.rename(columns={
        "team": "home_team",
        "opponent": "away_team",
    })

    # Odds normalization (unicode minus)
    df["odds"] = df["odds"].astype(str).str.replace("−", "-", regex=False)

    # Percent columns -> numeric decimals
    for col in ["handle_pct", "bets_pct"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("%", "", regex=False)
            .astype(float)
            / 100.0
        )

    # Market column
    df["market"] = "moneyline"

    out_path = OUTPUT_DIR / f"clean_dk_{league}_{year}_{month}_{day}.csv"

    if out_path.exists():
        old = pd.read_csv(out_path)
        if old.equals(df):
            return

    df.to_csv(out_path, index=False)


def main():
    for file in INPUT_DIR.glob("dk_*.csv"):
        clean_file(file)


if __name__ == "__main__":
    main()
