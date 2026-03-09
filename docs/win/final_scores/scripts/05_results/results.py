#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/results.py

import os
import glob
import re
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd


# =========================
# LOGGER
# =========================

def audit(log_path, stage, status, msg="", df=None):

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log_mode = "w" if not log_path.exists() else "a"

    with open(log_path, log_mode, encoding="utf-8") as f:

        f.write(f"\n[{ts}] [{stage}] {status}\n")

        if msg:
            f.write(f"  MSG: {msg}\n")

        if df is not None and isinstance(df, pd.DataFrame):

            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")

        f.write("-" * 40 + "\n")


ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG = ERROR_DIR / "results_errors.txt"


def log_error(message: str):

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def safe_read_csv(path: str):

    try:
        df = pd.read_csv(path)

        if df is None or df.empty:
            return pd.DataFrame()

        return df

    except Exception:

        log_error(f"ERROR READING {path}: {traceback.format_exc()}")

        return pd.DataFrame()


# =========================
# OUTCOME LOGIC
# =========================

def determine_outcome(row):

    try:

        m_type = str(row.get("market_type", "")).lower()
        side = str(row.get("bet_side", "")).lower()

        line = float(row.get("line", 0))

        away_s = float(row["away_score"])
        home_s = float(row["home_score"])

        if m_type == "total":

            total_score = away_s + home_s

            if total_score == line:
                return "Push"

            if side == "over":
                return "Win" if total_score > line else "Loss"

            if side == "under":
                return "Win" if total_score < line else "Loss"

            return "Unknown"

        if m_type == "moneyline":

            if away_s == home_s:
                return "Push"

            if side == "away":
                return "Win" if away_s > home_s else "Loss"

            if side == "home":
                return "Win" if home_s > away_s else "Loss"

        if m_type in ["spread", "puck_line"]:

            if side == "away":
                diff = (away_s + line) - home_s
            else:
                diff = (home_s + line) - away_s

            if diff == 0:
                return "Push"

            return "Win" if diff > 0 else "Loss"

        return "Unknown"

    except Exception:

        return "Unknown"


# =========================
# MASTER FILE BUILDER
# =========================

def write_market_master(cfg, output_dir):

    output_dir.mkdir(parents=True, exist_ok=True)

    master_path = output_dir / f"{cfg['name']}_final.csv"

    pattern = str(output_dir / f"*_results_{cfg['suffix']}.csv")

    files = sorted(glob.glob(pattern))

    if not files:

        audit(ERROR_LOG, "MASTER", "SKIP", msg=f"No graded files found for {cfg['name']}")
        return

    dfs = []

    for f in files:

        if Path(f).name.lower() == master_path.name.lower():
            continue

        df = safe_read_csv(f)

        if not df.empty:

            df = df[df["bet_side"].notna()]
            df = df[df["bet_side"] != ""]

            if not df.empty:
                dfs.append(df)

    if not dfs:

        audit(ERROR_LOG, "MASTER", "SKIP", msg=f"No valid bets found for {cfg['name']}")
        return

    master_df = pd.concat(dfs, ignore_index=True)

    preferred_order = [
        "game_date",
        "away_team",
        "home_team",
        "away_score",
        "home_score",
        "bet_result",
        "market",
        "market_type",
        "bet_side",
        "line",
        "home_ml_edge_decimal",
        "away_ml_edge_decimal",
        "home_spread_edge_decimal",
        "away_spread_edge_decimal",
        "over_edge_decimal",
        "under_edge_decimal",
    ]

    cols = [c for c in preferred_order if c in master_df.columns] + \
           [c for c in master_df.columns if c not in preferred_order]

    master_df = master_df[cols]

    master_df = master_df.drop_duplicates()

    master_df = master_df.sort_values(
        ["game_date", "market_type", "away_team", "home_team"],
        kind="mergesort"
    )

    master_df.to_csv(master_path, index=False)

    audit(ERROR_LOG, "MASTER", "SUCCESS",
          msg=f"Wrote {cfg['name']} master", df=master_df)


# =========================
# MAIN PROCESS
# =========================

def process_results():

    with open(ERROR_LOG, "w") as f:
        f.write("=== Results Script Log ===\n")

    configs = [
        {
            "name": "NBA",
            "scores_sub": "nba",
            "bets_dir": "docs/win/basketball/04_select/daily_slate",
            "suffix": "NBA",
            "pattern": "*_nba.csv"
        },
        {
            "name": "NCAAB",
            "scores_sub": "ncaab",
            "bets_dir": "docs/win/basketball/04_select/daily_slate",
            "suffix": "NCAAB",
            "pattern": "*_ncaab.csv"
        }
    ]

    for cfg in configs:

        scores_dir = Path(f"docs/win/final_scores/results/{cfg['scores_sub']}/final_scores")
        output_dir = Path(f"docs/win/final_scores/results/{cfg['scores_sub']}/graded")

        output_dir.mkdir(parents=True, exist_ok=True)

        # ONLY LOAD BET FILES FOR THIS LEAGUE
        bet_files = glob.glob(os.path.join(cfg["bets_dir"], cfg["pattern"]))

        dates = set()

        for fpath in bet_files:

            match = re.search(r"(\d{4}_\d{2}_\d{2})", os.path.basename(fpath))

            if match:
                dates.add(match.group(1))

        for date_str in sorted(dates):

            score_file = scores_dir / f"{date_str}_final_scores_{cfg['suffix']}.csv"

            if not score_file.exists():
                continue

            # STRICT FILE MATCHING BY LEAGUE
            daily_bets = glob.glob(
                os.path.join(cfg["bets_dir"], f"{date_str}*{cfg['pattern'].replace('*','')}")
            )

            dfs = []

            for bf in daily_bets:

                df = safe_read_csv(bf)

                if not df.empty:
                    dfs.append(df)

            if not dfs:
                continue

            bets_df = pd.concat(dfs, ignore_index=True)

            scores_df = safe_read_csv(str(score_file))

            if scores_df.empty:
                continue

            try:

                df = pd.merge(
                    bets_df,
                    scores_df,
                    on=["away_team", "home_team", "game_date"],
                    validate="many_to_one",
                    suffixes=("", "_scorefile"),
                )

            except Exception:

                log_error(f"MERGE ERROR {cfg['name']} {date_str}: {traceback.format_exc()}")
                continue

            df["bet_result"] = df.apply(determine_outcome, axis=1)

            df.to_csv(output_dir / f"{date_str}_results_{cfg['suffix']}.csv", index=False)

            audit(ERROR_LOG, "GRADING", "SUCCESS", msg=f"{cfg['name']} {date_str}", df=df)

        write_market_master(cfg, output_dir)


if __name__ == "__main__":
    process_results()
