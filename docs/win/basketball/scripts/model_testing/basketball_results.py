#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/basketball_results.py

import traceback
from datetime import datetime
from pathlib import Path

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
        if df is not None:
            f.write(f"  ROWS: {len(df)}\n")
        f.write("-" * 40 + "\n")


def safe_read_csv(path):
    try:
        df = pd.read_csv(path)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        return pd.DataFrame()


def determine_outcome(row):
    market = row["market_type"]
    side = row["bet_side"]
    line = float(row["line"])
    away = float(row["away_score"])
    home = float(row["home_score"])

    if market == "moneyline":
        if side == "home":
            return "Win" if home > away else "Loss"
        return "Win" if away > home else "Loss"

    if market == "spread":
        if side == "home":
            val = (home + line) - away
        else:
            val = (away + line) - home

        if val > 0:
            return "Win"
        if val < 0:
            return "Loss"
        return "Push"

    if market == "total":
        total = home + away
        if total == line:
            return "Push"
        if side == "over":
            return "Win" if total > line else "Loss"
        return "Win" if total < line else "Loss"

    return "Unknown"


def write_master(league, graded_dir):
    files = sorted(graded_dir.glob("*_results_*.csv"))
    if not files:
        return

    dfs = [safe_read_csv(f) for f in files]
    dfs = [df for df in dfs if not df.empty]
    if not dfs:
        return

    master = pd.concat(dfs, ignore_index=True).drop_duplicates()
    master = master.sort_values(["game_date", "market_type", "away_team", "home_team", "bet_side"])
    master.to_csv(graded_dir / f"{league}_final.csv", index=False)
    audit("MASTER", "SUCCESS", league, master)


def grade_league(bets_file, scores_dir, graded_dir, league):
    bets_df = safe_read_csv(bets_file)
    if bets_df.empty:
        audit("GRADE", "SKIP", f"No bets found for {league}")
        return

    bets_df["game_date"] = bets_df["game_date"].astype(str)

    for date in sorted(bets_df.game_date.unique()):
        score_file = Path(scores_dir) / f"{date}_final_scores_{league}.csv"
        if not score_file.exists():
            audit("GRADE", "SKIP", f"Missing score file: {score_file}")
            continue

        scores_df = safe_read_csv(score_file)
        if scores_df.empty:
            continue

        daily = bets_df[bets_df.game_date == date].copy()
        merged = pd.merge(
            daily,
            scores_df,
            on=["away_team", "home_team", "game_date"],
            how="inner",
        )

        if merged.empty:
            audit("GRADE", "SKIP", f"No merge rows for {league} {date}")
            continue

        merged["bet_result"] = merged.apply(determine_outcome, axis=1)

        keep_cols = [
            "game_date",
            "away_team",
            "home_team",
            "away_score",
            "home_score",
            "market_type",
            "bet_side",
            "line",
            "take_odds",
            "candidate_edge",
            "odds_band",
            "line_band",
            "bet_result",
        ]

        out = merged[[col for col in keep_cols if col in merged.columns]].copy()
        out.to_csv(graded_dir / f"{date}_results_{league}.csv", index=False)


def process_results():
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("Basketball grading log\n")

    grade_league(
        Path("docs/win/basketball/04_select/nba_selected.csv"),
        "docs/win/final_scores/results/nba/final_scores",
        NBA_GRADED,
        "NBA",
    )

    grade_league(
        Path("docs/win/basketball/04_select/ncaab_selected.csv"),
        "docs/win/final_scores/results/ncaab/final_scores",
        NCAAB_GRADED,
        "NCAAB",
    )

    write_master("NBA", NBA_GRADED)
    write_master("NCAAB", NCAAB_GRADED)


if __name__ == "__main__":
    process_results()
