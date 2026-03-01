#!/usr/bin/env python3
# docs/win/final_scores/scripts/00_parsing/dedupe.py

import sys
from pathlib import Path
import pandas as pd
import traceback

BASE_DIR = Path("docs/win/final_scores")
ERROR_DIR = BASE_DIR / "errors"
ERROR_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG = ERROR_DIR / "dedupe.txt"


def main():
    with open(ERROR_LOG, "w") as log:
        try:
            files = sorted(BASE_DIR.glob("*_final_scores_*.csv"))

            if not files:
                log.write("No final score files found.\n")
                return

            for path in files:
                df = pd.read_csv(path)

                if df.empty:
                    log.write(f"{path.name}: empty file\n")
                    continue

                before = len(df)

                # Define dedupe key
                key_cols = [
                    "game_date",
                    "market",
                    "away_team",
                    "home_team"
                ]

                # Only use columns that exist (safety)
                key_cols = [c for c in key_cols if c in df.columns]

                df = df.drop_duplicates(subset=key_cols, keep="last")

                after = len(df)

                df.to_csv(path, index=False)

                log.write(f"{path.name}: {before} -> {after} rows\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()
