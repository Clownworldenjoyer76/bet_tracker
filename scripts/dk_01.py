#scripts/dk_01.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import re
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual")
OUTPUT_DIR = INPUT_DIR / "cleaned"
ERROR_DIR = Path("docs/win/errors")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ERROR_LOG = ERROR_DIR / f"dk_1_{TIMESTAMP}.txt"

# =========================
# HELPERS
# =========================

def log_error(msg: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def normalize_date(date_str: str, year: int) -> str:
    month, day = date_str.split("/")
    return f"{year}_{int(month):02d}_{int(day):02d}"


def normalize_time(time_str: str) -> str:
    s = str(time_str).strip().upper().replace(" ", "")
    m = re.match(r"(\d{1,2}:\d{2})(AM|PM)", s)
    if not m:
        return time_str
    return f"{m.group(1)} {m.group(2)}"


def american_to_decimal(odds: float) -> float:
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / abs(odds)

# =========================
# CORE LOGIC
# =========================

def process_file(path: Path):
    try:
        df = pd.read_csv(path)

        # Filename: dk_{league}_{market}_{YYYY}_{MM}_{DD}.csv
        parts = path.stem.split("_")
        if len(parts) < 6:
            raise ValueError(f"Invalid filename format: {path.name}")

        _, league, market, year, month, day = parts
        year = int(year)

        # ---- REQUIRED CHANGE ----
        # Overwrite league column using filename
        df["league"] = f"{league}_{market}"
        # -------------------------

        # Date normalization
        df["date"] = df["date"].apply(lambda x: normalize_date(str(x), year))

        # Time normalization
        df["time"] = df["time"].apply(normalize_time)

        # Odds normalization (string-level)
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

        # game_id column (blank)
        df["game_id"] = ""

        # Write output
        out_path = OUTPUT_DIR / path.name
        df.to_csv(out_path, index=False)

    except Exception as e:
        log_error(f"FILE: {path}")
        log_error(str(e))
        log_error(traceback.format_exc())
        log_error("-" * 80)

# =========================
# MAIN
# =========================

def main():
    patterns = [
        "dk_*_moneyline_*.csv",
        "dk_*_spreads_*.csv",
        "dk_*_totals_*.csv",
    ]

    for pattern in patterns:
        for file in INPUT_DIR.glob(pattern):
            process_file(file)


if __name__ == "__main__":
    main()
