# File: scripts/manual_clean.py
"""
Skeleton script for manually cleaning DraftKings CSV dumps.

Input:
  docs/win/manual/*.csv

Output:
  docs/win/manual/cleaned/clean_dk_{league}_{year}_{month}_{day}.csv

Behavior:
- Normalize date to M/D/YYYY
- Normalize time to HH:MM AM/PM
- Retain team/opponent semantics (no home/away inference)
- Normalize odds minus sign
- Convert handle/bets percentages to numeric decimals
- Add market column
- If output exists, update only if changes are detected
- If no changes, exit silently
"""

from pathlib import Path
import pandas as pd
import re

INPUT_DIR = Path("docs/win/manual")
OUTPUT_DIR = INPUT_DIR / "cleaned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_date(date_str: str, year: int) -> str:
    """
    Convert M/D or MM/DD -> M/D/YYYY
    """
    month, day = date_str.split("/")
    return f"{int(month)}/{int(day)}/{year}"


def normalize_time(time_str: str) -> str:
    """
    Convert:
      03:55PM  -> 03:55 PM
      3:55PM   -> 03:55 PM
      03:55 PM -> 03:55 PM
    """
    s = time_str.strip().upper().replace(" ", "")
    match = re.match(r"(\d{1,2}:\d{2})(AM|PM)", s)
    if not match:
        return time_str  # fail safe

    time_part, meridiem = match.groups()
    hour, minute = time_part.split(":")
    return f"{int(hour):02d}:{minute} {meridiem}"


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

    # Retain neutral team/opponent semantics
    # (home/away cannot be inferred safely at this stage)

    # Odds normalization (unicode minus)
    df["odds"] = df["odds"].astype(str).str.replace("−", "-", regex=False)

    # Percent columns -> numeric decimals
    for col in ("handle_pct", "bets_pct"):
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
