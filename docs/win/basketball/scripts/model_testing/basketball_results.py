#!/usr/bin/env python3
# basketball_results.py

import os
import glob
import re
import traceback
from pathlib import Path
from datetime import datetime

import pandas as pd

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG = ERROR_DIR / "basketball_results_errors.txt"

# optimizer-safe graded dirs
NBA_GRADED = Path("docs/win/basketball/model_testing/graded/nba")
NCAAB_GRADED = Path("docs/win/basketball/model_testing/graded/ncaab")

NBA_GRADED.mkdir(parents=True, exist_ok=True)
NCAAB_GRADED.mkdir(parents=True, exist_ok=True)


def audit(stage, status, msg="", df=None):

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg:
            f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")


def safe_read_csv(path):

    try:
        df = pd.read_csv(path)
        if df is None or df.empty:
            return pd.DataFrame()
        return df

    except Exception:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"ERROR READING {path}\n{traceback.format_exc()}\n")
        return pd.DataFrame()


def determine_outcome(row):

    try:

        m_type = str(row.get("market_type", "")).lower()
        side = str(row.get("bet_side", "")).lower()

        line = float(row.get("line", 0))

        away = float(row["away_score"])
        home = float(row["home_score"])

        if m_type == "total":

            total_score = away + home

            if total_score == line:
                return "Push"

            if side == "under":
                return "Win" if total_score < line else "Loss"

            if side == "over":
                return "Win" if total_score > line else "Loss"

        if m_type == "moneyline":

            if away == home:
                return "Push"

            if side == "away":
                return "Win" if away > home else "Loss"

            if side == "home":
                return "Win" if home > away else "Loss"

        if m_type == "spread":

            if side == "away":
                diff = (away + line) - home
            else:
                diff = (home + line) - away

            if diff == 0:
                return "Push"

            return "Win" if diff > 0 else "Loss"

        return "Unknown"

    except Exception:
        return "Unknown"


def write_master(league, graded_dir):

    master_file = graded_dir / f"{league}_final.csv"

    files = sorted(glob.glob(str(graded_dir / "*_results_*.csv")))

    if not files:
        return

    dfs = []

    for f in files:
        df = safe_read_csv(f)
        if not df.empty:
            dfs.append(df)

    if not dfs:
        return

    master = pd.concat(dfs, ignore_index=True).drop_duplicates()

    master = master.sort_values(
        ["game_date", "market_type", "away_team", "home_team"],
        ascending=True
    )

    master.to_csv(master_file, index=False)

    audit("MASTER", "SUCCESS", f"Wrote {league} master", master)


def process_results():

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== Basketball Results Log ===\n\n")

    configs = [

        {
            "league": "NBA",
            "scores_dir": "docs/win/final_scores/results/nba/final_scores",
            "bets_dir": "docs/win/basketball/04_select",
            "pattern": "*nba_selected.csv",
            "graded": NBA_GRADED
        },

        {
            "league": "NCAAB",
            "scores_dir": "docs/win/final_scores/results/ncaab/final_scores",
            "bets_dir": "docs/win/basketball/04_select",
            "pattern": "*ncaab_selected.csv",
            "graded": NCAAB_GRADED
        }

    ]

    for cfg in configs:

        scores_dir = Path(cfg["scores_dir"])
        graded_dir = cfg["graded"]

        bet_files = glob.glob(os.path.join(cfg["bets_dir"], cfg["pattern"]))

        dates = set()

        for f in bet_files:

            m = re.search(r"(\d{4}_\d{2}_\d{2})", os.path.basename(f))

            if m:
                dates.add(m.group(1))

        for date_str in sorted(dates):

            score_file = scores_dir / f"{date_str}_final_scores_{cfg['league']}.csv"

            if not score_file.exists():
                continue

            daily_bets = glob.glob(os.path.join(cfg["bets_dir"], f"{date_str}*.csv"))

            bet_dfs = []

            for bf in daily_bets:
                df = safe_read_csv(bf)
                if not df.empty:
                    bet_dfs.append(df)

            if not bet_dfs:
                continue

            bets_df = pd.concat(bet_dfs, ignore_index=True)

            scores_df = safe_read_csv(score_file)

            if scores_df.empty:
                continue

            try:

                merged = pd.merge(
                    bets_df,
                    scores_df,
                    on=["away_team", "home_team", "game_date"]
                )

            except Exception:

                with open(ERROR_LOG, "a") as f:
                    f.write(f"MERGE ERROR {cfg['league']} {date_str}\n")
                    f.write(traceback.format_exc())

                continue

            if merged.empty:
                continue

            merged["bet_result"] = merged.apply(determine_outcome, axis=1)

            cols = [
                "game_date",
                "away_team",
                "home_team",
                "away_score",
                "home_score",
                "bet_result",
                "market",
                "market_type",
                "bet_side",
                "line"
            ]

            out_df = merged[[c for c in cols if c in merged.columns]]

            output_path = graded_dir / f"{date_str}_results_{cfg['league']}.csv"

            out_df.to_csv(output_path, index=False)

            audit("GRADING", "SUCCESS", f"{cfg['league']} {date_str}", out_df)

        write_master(cfg["league"], graded_dir)


if __name__ == "__main__":
    process_results()
