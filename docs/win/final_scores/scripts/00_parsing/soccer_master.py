#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/soccer_master.py

import glob
import re
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd


INPUT_DIR = Path("docs/win/final_scores/results/soccer/final_scores")
ERROR_DIR = Path("docs/win/final_scores/errors")

ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "soccer_master_log.txt"


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def safe_read_csv(path):

    try:

        df = pd.read_csv(path)

        if df is None or df.empty:
            return pd.DataFrame()

        return df

    except Exception:

        log(
            f"ERROR reading {path}\n"
            f"{traceback.format_exc()}"
        )

        return pd.DataFrame()


def build_soccer_master():

    with open(LOG_FILE, "w") as f:
        f.write(f"=== Soccer Master Build | {datetime.now()} ===\n")

    pattern = str(INPUT_DIR / "*_final_scores_*.csv")

    files = glob.glob(pattern)

    if not files:
        log("No soccer score files found")
        return

    dates = {}

    for f in files:

        fname = Path(f).name

        # skip already-built master files
        if fname.endswith("_final_scores_SOCCER.csv"):
            continue

        match = re.search(r"(\d{4}_\d{2}_\d{2})", fname)

        if not match:
            continue

        date = match.group(1)

        dates.setdefault(date, []).append(f)

    if not dates:
        log("No dated soccer score files detected")
        return

    for date_str, file_list in sorted(dates.items()):

        dfs = []

        for f in file_list:

            df = safe_read_csv(f)

            if df.empty:
                continue

            # normalize column name for results.py merge
            if "match_date" in df.columns:
                df = df.rename(columns={"match_date": "game_date"})

            dfs.append(df)

        if not dfs:
            log(f"{date_str} skipped - no valid files")
            continue

        master_df = pd.concat(dfs, ignore_index=True)

        # sort for stability
        sort_cols = [c for c in ["game_date", "away_team", "home_team"] if c in master_df.columns]

        if sort_cols:
            master_df = master_df.sort_values(sort_cols, kind="mergesort")

        outfile = INPUT_DIR / f"{date_str}_final_scores_SOCCER.csv"

        master_df.to_csv(outfile, index=False)

        log(
            f"MASTER CREATED {outfile} | rows={len(master_df)}"
        )


if __name__ == "__main__":
    build_soccer_master()
