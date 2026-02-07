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


def normalize_date(date_str: str, year: int) -> str:
    date_str = str(date_str).strip()
    if "_" in date_str:
        return date_str
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
# TEAM MAP (MINIMAL)
# =========================

def load_team_map():
    team_map = {}
    for path in MAP_DIR.glob("team_map_*.csv"):
        df = pd.read_csv(path, dtype=str)
        for _, r in df.iterrows():
            lg = r["league"].split("_")[0].strip()
            team_map.setdefault(lg, {})[r["alias"].strip()] = r["canonical_team"].strip()
    return team_map


TEAM_MAP = load_team_map()

# =========================
# CORE LOGIC
# =========================

def process_file(path: Path):
    try:
        df = pd.read_csv(path)

        # dk_{league}_{market}_{YYYY}_{MM}_{DD}.csv
        parts = path.stem.split("_")
        if len(parts) < 6:
            raise ValueError(f"Invalid filename format: {path.name}")

        _, league, market, year, month, day = parts
        year = int(year)
        base_league = league

        # overwrite league using filename
        df["league"] = f"{league}_{market}"

        # Date / time
        df["date"] = df["date"].apply(lambda x: normalize_date(x, year))
        df["time"] = df["time"].apply(normalize_time)

        # Odds
        df["odds"] = (
            df["odds"]
            .astype(str)
            .str.replace("−", "-", regex=False)
            .str.lstrip("+")
        )

        df["decimal_odds"] = df["odds"].astype(float).apply(american_to_decimal)

        for col in ("handle_pct", "bets_pct"):
            if col in df.columns:
                df[col] = df[col].astype(float) / 100.0

        # 🔑 TEAM NORMALIZATION (THE FIX)
        for col in ("team", "opponent"):
            if col in df.columns and base_league in TEAM_MAP:
                df[col] = df[col].apply(
                    lambda v: TEAM_MAP[base_league].get(str(v).strip(), v)
                )

        df["game_id"] = ""

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
    for pattern in (
        "dk_*_moneyline_*.csv",
        "dk_*_spreads_*.csv",
        "dk_*_totals_*.csv",
    ):
        for file in INPUT_DIR.glob(pattern):
            process_file(file)

if __name__ == "__main__":
    main()
