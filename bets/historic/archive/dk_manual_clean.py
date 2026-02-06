import pandas as pd
from pathlib import Path
import re

INPUT_DIR = Path("docs/win/manual")
OUTPUT_DIR = INPUT_DIR / "cleaned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def normalize_date(date_str: str, year: int) -> str:
    month, day = date_str.split("/")
    return f"{year}_{int(month):02d}_{int(day):02d}"


def normalize_time(time_str: str) -> str:
    # "7:07PM" -> "7:07 PM"
    s = time_str.strip().upper().replace(" ", "")
    m = re.match(r"(\d{1,2}:\d{2})(AM|PM)", s)
    if not m:
        return time_str
    return f"{m.group(1)} {m.group(2)}"

def american_to_decimal(odds: float) -> float:
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / abs(odds)

def clean_file(path: Path):
    df = pd.read_csv(path)

    # Expected filename: dk_{league}_{market}_{YYYY}_{MM}_{DD}.csv
    parts = path.stem.split("_")
    if len(parts) < 6:
        return

    _, league, market, year, month, day = parts
    year = int(year)

    # Date / time
    df["date"] = df["date"].apply(lambda x: normalize_date(x, year))
    df["time"] = df["time"].apply(normalize_time)

    # Odds normalization
    df["odds"] = (
        df["odds"]
        .astype(str)
        .str.replace("−", "-", regex=False)
        .str.lstrip("+")
    )

    # Decimal odds
    df["decimal_odds"] = df["odds"].astype(float).apply(american_to_decimal)

    # Percent columns -> decimals
    for col in ("handle_pct", "bets_pct"):
        if col in df.columns:
            df[col] = df[col].astype(float) / 100.0

    out_path = OUTPUT_DIR / path.name

    # Check for changes before writing to avoid unnecessary updates


    df.to_csv(out_path, index=False)

def main():
    # Process Moneyline files
    for file in INPUT_DIR.glob("dk_*_moneyline_*.csv"):
        clean_file(file)

    # Process Spreads files
    for file in INPUT_DIR.glob("dk_*_spreads_*.csv"):
        clean_file(file)

    # Process Totals files (NEW)
    for file in INPUT_DIR.glob("dk_*_totals_*.csv"):
        clean_file(file)

if __name__ == "__main__":
    main()
