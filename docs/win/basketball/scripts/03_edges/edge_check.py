#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from datetime import datetime

# Setup paths
EDGE_DIR = Path("docs/win/basketball/03_edges")
ERROR_DIR = Path("docs/win/basketball/errors/03_edges")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "edge_check.txt"

def log_line(text):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(f"[{ts}] {text}\n")

def process_file(path):
    try:
        df = pd.read_csv(path)
        if df.empty:
            return 0
        
        name = path.name.lower()
        
        # MONEYLINE
        if "moneyline" in name:
            df["home_ml_edge_decimal"] = df["home_dk_decimal_moneyline"] - df["home_juice_decimal_moneyline"]
            df["away_ml_edge_decimal"] = df["away_dk_decimal_moneyline"] - df["away_juice_decimal_moneyline"]

        # SPREAD
        elif "spread" in name:
            df["home_spread_edge_decimal"] = df["home_dk_spread_decimal"] - df["home_spread_juice_decimal"]
            df["away_spread_edge_decimal"] = df["away_dk_spread_decimal"] - df["away_spread_juice_decimal"]

        # TOTAL
        elif "total" in name:
            df["over_edge_decimal"] = df["dk_total_over_decimal"] - df["total_over_juice_decimal"]
            df["under_edge_decimal"] = df["dk_total_under_decimal"] - df["total_under_juice_decimal"]

        # Save and finish
        df.to_csv(path, index=False)
        log_line(f"SUCCESS | {path.name}")
        return 1

    except Exception as e:
        log_line(f"FAILED | {path.name} | Error: {str(e)}")
        return 0

def main():
    # Clear old log
    with open(LOG_FILE, "w") as fh:
        fh.write("EDGE CHECK REPORT\n" + "="*30 + "\n")

    patterns = ["*_moneyline.csv", "*_spread.csv", "*_total.csv"]
    files = []
    for p in patterns:
        files.extend(EDGE_DIR.glob(p))

    processed_count = sum(process_file(f) for f in files)
    log_line(f"SUMMARY | Files Processed: {processed_count}")

if __name__ == "__main__":
    main()
