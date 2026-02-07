#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import re
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/first")
OUTPUT_DIR = INPUT_DIR / "cleaned"
ERROR_DIR = Path("docs/win/errors")
MAP_DIR = Path("mappings")

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

def norm(s):
    return " ".join(str(s).split()) if s is not None else ""

def load_team_map(league: str):
    path = MAP_DIR / f"team_map_{league}.csv"
    if not path.exists():
        return {}

    df = pd.read_csv(path, dtype=str)
    return {
        norm(r["alias"]): norm(r["canonical_team"])
        for _, r in df.iterrows()
    }

def normalize_date(date_str: str, year: int) -> str:
    date_str = str(date_str).strip()
    if "_" in date_str:
        return date_str
    m, d = date_str.split("/")
    return f"{year}_{int(m):02d}_{int(d):02d}"

def normalize_time(time_str: str) -> str:
    s = str(time_str).strip().upper().replace(" ", "")
    m = re.match(r"(\d{1,2}:\d{2})(AM|PM)", s)
    return f"{m.group(1)} {m.group(2)}" if m else time_str

def american_to_decimal(odds: float) -> float:
    return 1 + odds / 100 if odds > 0 else 1 + 100 / abs(odds)

# =========================
# CORE
# =========================

def process_file(path: Path):
    try:
        df = pd.read_csv(path)

        # dk_{league}_{market}_{YYYY}_{MM}_{DD}.csv
        _, league, market, year, *_ = path.stem.split("_")
        year = int(year)

        team_map = load_team_map(league)

        # enforce league
        df["league"] = f"{league}_{market}"

        # normalize date/time
        df["date"] = df["date"].apply(lambda x: normalize_date(x, year))
        df["time"] = df["time"].apply(normalize_time)

        # *** THE FIX ***
        df["team"] = df["team"].apply(lambda t: team_map.get(norm(t), norm(t)))
        df["opponent"] = df["opponent"].apply(lambda t: team_map.get(norm(t), norm(t)))

        # odds
        df["odds"] = (
            df["odds"].astype(str)
            .str.replace("−", "-", regex=False)
            .str.lstrip("+")
        )

        df["decimal_odds"] = df["odds"].astype(float).apply(american_to_decimal)

        for col in ("handle_pct", "bets_pct"):
            if col in df.columns:
                df[col] = df[col].astype(float) / 100.0

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
