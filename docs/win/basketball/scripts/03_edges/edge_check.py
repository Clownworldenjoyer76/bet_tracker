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


def edge(model_decimal, book_decimal):
    model_decimal = pd.to_numeric(model_decimal, errors="coerce")
    book_decimal = pd.to_numeric(book_decimal, errors="coerce")
    return (1 / model_decimal) - (1 / book_decimal)


def rebuild_edges(df):

    updated = 0

    def update(col, new_vals):
        nonlocal updated
        if col not in df.columns:
            return
        old = df[col].copy()
        df[col] = new_vals
        updated += (old != new_vals).sum()

    if {"home_spread_juice_decimal", "home_dk_spread_decimal"}.issubset(df.columns):
        new_vals = edge(df["home_spread_juice_decimal"], df["home_dk_spread_decimal"])
        update("home_spread_edge_decimal", new_vals)

    if {"away_spread_juice_decimal", "away_dk_spread_decimal"}.issubset(df.columns):
        new_vals = edge(df["away_spread_juice_decimal"], df["away_dk_spread_decimal"])
        update("away_spread_edge_decimal", new_vals)

    if {"home_juice_decimal_moneyline", "home_dk_decimal_moneyline"}.issubset(df.columns):
        new_vals = edge(df["home_juice_decimal_moneyline"], df["home_dk_decimal_moneyline"])
        update("home_ml_edge_decimal", new_vals)

    if {"away_juice_decimal_moneyline", "away_dk_decimal_moneyline"}.issubset(df.columns):
        new_vals = edge(df["away_juice_decimal_moneyline"], df["away_dk_decimal_moneyline"])
        update("away_ml_edge_decimal", new_vals)

    if {"total_over_juice_decimal", "dk_total_over_decimal"}.issubset(df.columns):
        new_vals = edge(df["total_over_juice_decimal"], df["dk_total_over_decimal"])
        update("over_edge_decimal", new_vals)

    if {"total_under_juice_decimal", "dk_total_under_decimal"}.issubset(df.columns):
        new_vals = edge(df["total_under_juice_decimal"], df["dk_total_under_decimal"])
        update("under_edge_decimal", new_vals)

    return df, updated


def process_file(path):

    try:
        df = pd.read_csv(path)

        if df.empty:
            log_line(f"SKIP empty file | {path.name}")
            return 0

        df, updates = rebuild_edges(df)
        df.to_csv(path, index=False)

        log_line(f"UPDATED | {path.name} | values_updated={updates}")

        return updates

    except Exception:
        log_line(f"FAILED | {path.name}\n{traceback.format_exc()}")
        return 0


def main():

    reset_log()

    files = []
    for pattern in PATTERNS:
        files.extend(sorted(EDGE_DIR.glob(pattern)))

    if not files:
        log_line("No edge files found.")
        return

    total_files = 0
    total_updates = 0

    for f in files:
        total_files += 1
        total_updates += process_file(f)

    log_line("-" * 80)
    log_line(f"SUMMARY | files_processed={total_files} | values_updated={total_updates}")


if __name__ == "__main__":
    main()
