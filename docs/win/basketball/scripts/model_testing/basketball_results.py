#!/usr/bin/env python3
# basketball_results.py

import traceback
from pathlib import Path
from datetime import datetime

import pandas as pd

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG = ERROR_DIR / "basketball_results_errors.txt"

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

    files = sorted(graded_dir.glob("*_results_*.csv"))

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


def grade_league(bets_file, scores_dir, graded_dir, league):

    bets_df = safe_read_csv(bets_file)

    if bets_df.empty:
        return

    for date_str in sorted(bets_df["game_date"].unique()):

        score_file = Path(scores_dir) / f"{date_str}_final_scores_{league}.csv"

        if not score_file.exists():
            continue

        scores_df = safe_read_csv(score_file)

        if scores_df.empty:
            continue

        daily_bets = bets_df[bets_df["game_date"] == date_str]

        try:

            merged = pd.merge(
                daily_bets,
                scores_df,
                on=["away_team", "home_team", "game_date"]
            )

        except Exception:

            with open(ERROR_LOG, "a") as f:
                f.write(f"MERGE ERROR {league} {date_str}\n")
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

        output_path = graded_dir / f"{date_str}_results_{league}.csv"

        out_df.to_csv(output_path, index=False)

        audit("GRADING", "SUCCESS", f"{league} {date_str}", out_df)

    write_master(league, graded_dir)


def process_results():

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== Basketball Results Log ===\n\n")

    grade_league(
        Path("docs/win/basketball/04_select/nba_selected.csv"),
        "docs/win/final_scores/results/nba/final_scores",
        NBA_GRADED,
        "NBA"
    )

    grade_league(
        Path("docs/win/basketball/04_select/ncaab_selected.csv"),
        "docs/win/final_scores/results/ncaab/final_scores",
        NCAAB_GRADED,
        "NCAAB"
    )


if __name__ == "__main__":
    process_results()
