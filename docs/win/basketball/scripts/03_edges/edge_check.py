#!/usr/bin/env python3
# docs/win/basketball/scripts/03_edges/edge_check.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

EDGE_DIR = Path("docs/win/basketball/03_edges")
ERROR_DIR = Path("docs/win/basketball/errors/03_edges")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "edge_check.txt"

PATTERNS = [
    "*_basketball_NBA_moneyline.csv",
    "*_basketball_NBA_spread.csv",
    "*_basketball_NBA_total.csv",
    "*_basketball_NCAAB_moneyline.csv",
    "*_basketball_NCAAB_spread.csv",
    "*_basketball_NCAAB_total.csv",
]


def log_line(text):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(f"[{ts}] {text}\n")


def reset_log():
    with open(LOG_FILE, "w", encoding="utf-8") as fh:
        fh.write("EDGE CHECK REPORT\n")
        fh.write("=" * 80 + "\n")


def process_file(path):

    try:

        df = pd.read_csv(path)
        name = path.name.lower()

        if df.empty:
            log_line(f"SKIP empty file | {path.name}")
            return 0

        updated = 0

        # ---------------------------
        # MONEYLINE FILES
        # ---------------------------

        if "moneyline" in name:

            new_home = df["home_dk_decimal_moneyline"] - df["home_juice_decimal_moneyline"]
            new_away = df["away_dk_decimal_moneyline"] - df["away_juice_decimal_moneyline"]

            updated += (df["home_ml_edge_decimal"] != new_home).sum()
            updated += (df["away_ml_edge_decimal"] != new_away).sum()

            df["home_ml_edge_decimal"] = new_home
            df["away_ml_edge_decimal"] = new_away


        # ---------------------------
        # SPREAD FILES
        # ---------------------------

        elif "spread" in name:

            new_home = df["home_dk_spread_decimal"] - df["home_spread_juice_decimal"]
            new_away = df["away_dk_spread_decimal"] - df["away_spread_juice_decimal"]

            updated += (df["home_spread_edge_decimal"] != new_home).sum()
            updated += (df["away_spread_edge_decimal"] != new_away).sum()

            df["home_spread_edge_decimal"] = new_home
            df["away_spread_edge_decimal"] = new_away


        # ---------------------------
        # TOTAL FILES
        # ---------------------------

        elif "total" in name:

            new_over = df["dk_total_over_decimal"] - df["total_over_juice_decimal"]
            new_under = df["dk_total_under_decimal"] - df["total_under_juice_decimal"]

            updated += (df["over_edge_decimal"] != new_over).sum()
            updated += (df["under_edge_decimal"] != new_under).sum()

            df["over_edge_decimal"] = new_over
            df["under_edge_decimal"] = new_under


        df.to_csv(path, index=False)

        log_line(f"UPDATED | {path.name} | values_updated={updated}")

        return updated

    except Exception:

        log_line(f"FAILED | {path.name}\n{traceback.format_exc()}")
        return 0


def main():

    reset_log()

    files = []

    for pattern in PATTERNS:
        files.extend(sorted(EDGE_DIR.glob(pattern)))

    total_files = 0
    total_updates = 0

    for f in files:
        total_files += 1
        total_updates += process_file(f)

    log_line("-" * 80)
    log_line(f"SUMMARY | files_processed={total_files} | values_updated={total_updates}")


if __name__ == "__main__":
    main()
