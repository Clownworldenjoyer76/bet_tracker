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
        with open(ERROR_LOG, "a") as f:
            f.write(traceback.format_exc())
        return pd.DataFrame()


def determine_outcome(row):

    m = row["market_type"]
    side = row["bet_side"]
    line = float(row["line"])

    away = row["away_score"]
    home = row["home_score"]

    if m == "moneyline":

        if side == "home":
            return "Win" if home > away else "Loss"
        else:
            return "Win" if away > home else "Loss"

    if m == "spread":

        if side == "home":
            val = (home + line) - away
        else:
            val = (away + line) - home

        if val > 0:
            return "Win"
        if val < 0:
            return "Loss"
        return "Push"

    if m == "total":

        total = home + away

        if total == line:
            return "Push"

        if side == "over":
            return "Win" if total > line else "Loss"
        else:
            return "Win" if total < line else "Loss"

    return "Unknown"


def bucket_stats(df, col, bins):

    if col not in df.columns:
        return pd.DataFrame()

    temp = df.copy()
    temp[col] = pd.to_numeric(temp[col], errors="coerce")
    temp = temp.dropna(subset=[col])

    temp["bucket"] = pd.cut(temp[col], bins=bins, include_lowest=True)

    g = temp.groupby("bucket")

    res = pd.DataFrame({
        "bucket": g.size().index.astype(str),
        "bets": g.size().values,
        "wins": g.apply(lambda x: (x.bet_result == "Win").sum()).values
    })

    res["win_pct"] = res["wins"] / res["bets"]

    return res


def write_analysis(master, league, out_dir):

    ml = master[master.market_type == "moneyline"]
    spreads = master[master.market_type == "spread"]
    totals = master[master.market_type == "total"]

    odds_bins = [-1000,-400,-300,-200,-150,-110,0,100,200,400,1000]
    spread_bins = [-30,-15,-10,-7,-5,-3,-1,0,1,3,5,7,10,15,30]
    total_bins = [120,130,135,140,145,150,155,160,165,170,200]

    bucket_stats(
        ml[ml.bet_side=="home"],"line",odds_bins
    ).to_csv(out_dir/f"{league}_ml_home_odds.csv",index=False)

    bucket_stats(
        ml[ml.bet_side=="away"],"line",odds_bins
    ).to_csv(out_dir/f"{league}_ml_away_odds.csv",index=False)

    bucket_stats(
        spreads[spreads.bet_side=="home"],"line",spread_bins
    ).to_csv(out_dir/f"{league}_spread_home_band.csv",index=False)

    bucket_stats(
        spreads[spreads.bet_side=="away"],"line",spread_bins
    ).to_csv(out_dir/f"{league}_spread_away_band.csv",index=False)

    bucket_stats(
        totals[totals.bet_side=="over"],"line",total_bins
    ).to_csv(out_dir/f"{league}_total_over_band.csv",index=False)

    bucket_stats(
        totals[totals.bet_side=="under"],"line",total_bins
    ).to_csv(out_dir/f"{league}_total_under_band.csv",index=False)


def write_master(league, graded_dir):

    files = sorted(graded_dir.glob("*_results_*.csv"))

    if not files:
        return

    dfs = [safe_read_csv(f) for f in files]

    master = pd.concat(dfs, ignore_index=True).drop_duplicates()

    master = master.sort_values(
        ["game_date","market_type","away_team","home_team"]
    )

    master.to_csv(graded_dir/f"{league}_final.csv",index=False)

    write_analysis(master,league,graded_dir)

    audit("MASTER","SUCCESS",league,master)


def grade_league(bets_file,scores_dir,graded_dir,league):

    bets_df = safe_read_csv(bets_file)

    if bets_df.empty:
        return

    for date in sorted(bets_df.game_date.unique()):

        score_file = Path(scores_dir)/f"{date}_final_scores_{league}.csv"

        if not score_file.exists():
            continue

        scores_df = safe_read_csv(score_file)

        daily = bets_df[bets_df.game_date==date]

        merged = pd.merge(
            daily,
            scores_df,
            on=["away_team","home_team","game_date"]
        )

        if merged.empty:
            continue

        merged["bet_result"] = merged.apply(determine_outcome,axis=1)

        cols = [
            "game_date","away_team","home_team",
            "away_score","home_score",
            "bet_result","market_type","bet_side","line"
        ]

        out = merged[cols]

        out.to_csv(
            graded_dir/f"{date}_results_{league}.csv",
            index=False
        )


def process_results():

    with open(ERROR_LOG,"w") as f:
        f.write("Basketball grading log\n")

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

    write_master("NBA",NBA_GRADED)
    write_master("NCAAB",NCAAB_GRADED)


if __name__ == "__main__":
    process_results()
