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


def win_pct(df):
    return (df["bet_result"] == "Win").mean() if len(df) else 0.0


def bucket(series, bins):
    return pd.cut(series, bins=bins, include_lowest=True)


def bucket_table(df, value_col, bins, label):

    if value_col not in df.columns:
        return pd.DataFrame()

    temp = df.copy()
    temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")

    temp = temp.dropna(subset=[value_col])

    if temp.empty:
        return pd.DataFrame()

    temp["bucket"] = bucket(temp[value_col], bins)

    g = temp.groupby("bucket")

    res = pd.DataFrame({
        "bucket": g.size().index.astype(str),
        "bets": g.size().values,
        "wins": g.apply(lambda x: (x.bet_result == "Win").sum()).values,
    })

    res["win_pct"] = res["wins"] / res["bets"]

    res.insert(0, "metric", label)

    return res


def compute_analysis_tables(master, league, graded_dir):

    tables = []

    spreads = master[master["market_type"] == "spread"]
    totals = master[master["market_type"] == "total"]
    ml = master[master["market_type"] == "moneyline"]

    ml_home = ml[ml["bet_side"] == "home"]
    ml_away = ml[ml["bet_side"] == "away"]

    total_over = totals[totals["bet_side"] == "over"]
    total_under = totals[totals["bet_side"] == "under"]

    edge_bins = [0, .02, .04, .06, .08, .10, .12, .20, 1]
    odds_bins = [-1000, -400, -300, -200, -150, -100, 0, 100, 200, 400, 1000]
    diff_bins = [0, 2, 4, 6, 8, 12, 20]

    tables.append(bucket_table(total_over, "over_edge_decimal", edge_bins, f"{league}_TOTAL_OVER_EDGE"))
    tables.append(bucket_table(total_under, "under_edge_decimal", edge_bins, f"{league}_TOTAL_UNDER_EDGE"))

    tables.append(bucket_table(spreads, "home_edge_decimal", edge_bins, f"{league}_SPREAD_HOME_EDGE"))
    tables.append(bucket_table(spreads, "away_edge_decimal", edge_bins, f"{league}_SPREAD_AWAY_EDGE"))

    tables.append(bucket_table(ml_home, "home_edge_decimal", edge_bins, f"{league}_ML_HOME_EDGE"))
    tables.append(bucket_table(ml_away, "away_edge_decimal", edge_bins, f"{league}_ML_AWAY_EDGE"))

    tables.append(bucket_table(ml_home, "line", odds_bins, f"{league}_ML_HOME_ODDS"))
    tables.append(bucket_table(ml_away, "line", odds_bins, f"{league}_ML_AWAY_ODDS"))

    if "total_projected_points" in totals.columns and "line" in totals.columns:
        totals = totals.copy()
        totals["proj_diff"] = abs(totals["total_projected_points"] - totals["line"])
        tables.append(bucket_table(totals, "proj_diff", diff_bins, f"{league}_TOTAL_PROJECTION_DIFF"))

    tables = [t for t in tables if not t.empty]

    if tables:
        analysis = pd.concat(tables, ignore_index=True)
        analysis.to_csv(graded_dir / f"{league}_analysis_tables.csv", index=False)


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

    compute_analysis_tables(master, league, graded_dir)

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
            with open(ERROR_LOG, "a", encoding="utf-8") as f:
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
            "line",
            "home_edge_decimal",
            "away_edge_decimal",
            "over_edge_decimal",
            "under_edge_decimal",
            "total_projected_points",
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
