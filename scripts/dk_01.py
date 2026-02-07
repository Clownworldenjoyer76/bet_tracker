#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/first")
OUTPUT_DIR = Path("docs/win/manual/cleaned")
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

def american_to_decimal(odds: float) -> float:
    return 1 + odds / 100 if odds > 0 else 1 + 100 / abs(odds)

# =========================
# CORE
# =========================

def process_file(path: Path):
    try:
        df = pd.read_csv(path)

        # dk_{league}_{market}_{YYYY}_{MM}_{DD}.csv
        _, league, market, *_ = path.stem.split("_")

        # enforce league
        df["league"] = f"{league}_{market}"

        # odds cleanup
        df["odds"] = (
            df["odds"].astype(str)
            .str.replace("−", "-", regex=False)
            .str.lstrip("+")
        )

        df["decimal_odds"] = df["odds"].astype(float).apply(american_to_decimal)

        # percentage normalization
        for col in ("handle_pct", "bets_pct"):
            if col in df.columns:
                df[col] = df[col].astype(float) / 100.0

        # placeholder
        df["game_id"] = ""

        df.to_csv(OUTPUT_DIR / path.name, index=False)

    except Exception as e:
        log_error(f"FILE: {path}")
        log_error(str(e))
        log_error(traceback.format_exc())
        log_error("-" * 80)

# =========================
# MAIN
# =========================

def main():
    for file in INPUT_DIR.glob("dk_*_*.csv"):
        process_file(file)

if __name__ == "__main__":
    main()
