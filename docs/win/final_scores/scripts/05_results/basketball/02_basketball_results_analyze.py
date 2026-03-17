#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/basketball_results_analyze.py

from datetime import datetime
from pathlib import Path

import pandas as pd

###############################################################
######################## PATH CONFIG ##########################
###############################################################

NBA_OUTPUT = Path("docs/win/final_scores/results/nba/graded")
NCAAB_OUTPUT = Path("docs/win/final_scores/results/ncaab/graded")

INTERMEDIATE_DIR = Path("docs/win/final_scores/intermediate")
INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ANALYZE_ERROR_LOG = ERROR_DIR / "basketball_results_analyze_errors.txt"
ANALYZE_SUMMARY_LOG = ERROR_DIR / "basketball_results_analyze_summary.txt"

###############################################################
######################## LOGGING ##############################
###############################################################

def reset_logs():
    ANALYZE_ERROR_LOG.write_text("", encoding="utf-8")
    ANALYZE_SUMMARY_LOG.write_text("", encoding="utf-8")


def log_error(msg):
    with open(ANALYZE_ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")


def log_summary(msg):
    with open(ANALYZE_SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

###############################################################
######################## HELPERS ##############################
###############################################################

def safe_read(path):
    try:
        path = Path(path)

        if not path.exists():
            log_error(f"MISSING FILE | {path}")
            return pd.DataFrame()

        df = pd.read_csv(path)

        if df is None or df.empty:
            log_error(f"EMPTY FILE | {path}")
            return pd.DataFrame()

        return df

    except Exception as e:
        log_error(f"READ ERROR | {path} | {e}")
        return pd.DataFrame()


def to_float(value):
    try:
        return float(value)
    except:
        return pd.NA

###############################################################
######################## SUMMARY CORE #########################
###############################################################

def summarize(df):
    if df is None or df.empty or "bet_result" not in df.columns:
        return 0, 0, 0, 0, 0.0

    wins = int((df["bet_result"] == "Win").sum())
    losses = int((df["bet_result"] == "Loss").sum())
    pushes = int((df["bet_result"] == "Push").sum())
    total = wins + losses + pushes
    win_pct = (wins / (wins + losses)) if (wins + losses) > 0 else 0.0

    return wins, losses, pushes, total, round(win_pct, 4)

###############################################################
######################## DERIVED FIELDS #######################
###############################################################

def side_group_from_bet_side(row):
    market_type = str(row.get("market_type", "")).strip().lower()
    bet_side = str(row.get("bet_side", "")).strip().lower()

    if market_type in {"moneyline", "spread"}:
        if "home" in bet_side:
            return "HOME"
        if "away" in bet_side:
            return "AWAY"

    if market_type == "total":
        if "over" in bet_side:
            return "OVER"
        if "under" in bet_side:
            return "UNDER"

    return ""


def selected_edge(row):
    market_type = str(row.get("market_type", "")).strip().lower()
    side_group = row.get("side_group", "")

    if market_type == "moneyline":
        if side_group == "HOME":
            return to_float(row.get("home_ml_edge_decimal"))
        if side_group == "AWAY":
            return to_float(row.get("away_ml_edge_decimal"))

    if market_type == "spread":
        if side_group == "HOME":
            return to_float(row.get("home_spread_edge_decimal"))
        if side_group == "AWAY":
            return to_float(row.get("away_spread_edge_decimal"))

    if market_type == "total":
        if side_group == "OVER":
            return to_float(row.get("over_edge_decimal"))
        if side_group == "UNDER":
            return to_float(row.get("under_edge_decimal"))

    return pd.NA


def selected_moneyline_odds(row):
    side_group = row.get("side_group", "")

    if side_group == "HOME":
        return to_float(row.get("home_dk_moneyline_american"))
    if side_group == "AWAY":
        return to_float(row.get("away_dk_moneyline_american"))

    return pd.NA


def selected_spread_line(row):
    side_group = row.get("side_group", "")

    if side_group == "HOME":
        return to_float(row.get("home_spread_x"))
    if side_group == "AWAY":
        return to_float(row.get("away_spread_x"))

    return pd.NA


def selected_total_line(row):
    return to_float(row.get("total_x"))

###############################################################
######################## BUCKETS ##############################
###############################################################

def edge_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return "UNBUCKETED"

    if val < 0:
        return "<0"
    if val < 0.01:
        return "0.00_to_0.0099"
    if val < 0.02:
        return "0.01_to_0.0199"
    if val < 0.03:
        return "0.02_to_0.0299"
    if val < 0.04:
        return "0.03_to_0.0399"
    if val < 0.05:
        return "0.04_to_0.0499"
    if val < 0.075:
        return "0.05_to_0.0749"
    if val < 0.10:
        return "0.075_to_0.0999"
    return "0.10_plus"


def spread_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return "UNBUCKETED"

    try:
        val = float(val)
    except:
        return "UNBUCKETED"

    base = int(val)

    if val >= 0:
        low = base + 0.5
        high = base + 1.4
    else:
        low = base - 0.5
        high = base - 1.4

    bucket_low = min(low, high)
    bucket_high = max(low, high)

    return f"{bucket_low:.1f}_to_{bucket_high:.1f}"


def odds_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return "UNBUCKETED"

    if val <= -200:
        return "minus_200_or_lower"
    if val <= -150:
        return "minus_199_to_minus_150"
    if val <= -125:
        return "minus_149_to_minus_125"
    if val <= -110:
        return "minus_124_to_minus_110"
    if val <= -101:
        return "minus_109_to_minus_101"
    if val <= 100:
        return "minus_100_to_plus_100"
    if val <= 125:
        return "plus_101_to_plus_125"
    if val <= 150:
        return "plus_126_to_plus_150"
    if val <= 200:
        return "plus_151_to_plus_200"
    return "plus_201_or_higher"


def total_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return "UNBUCKETED"

    start = int(val // 5) * 5
    end = start + 4.9
    return f"{start}_to_{end:.1f}"

###############################################################
######################## PREP ANALYTICS #######################
###############################################################

def prepare_work_df(df, league):
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    if "bet_result" in work.columns:
        work["bet_result"] = work["bet_result"].astype(str).str.strip().str.title()

    work["market"] = league
    work["market_type"] = work["market_type"].astype(str).str.strip().str.lower()
    work["side_group"] = work.apply(side_group_from_bet_side, axis=1)
    work["selected_edge"] = work.apply(selected_edge, axis=1)
    work["moneyline_odds_value"] = work.apply(selected_moneyline_odds, axis=1)
    work["spread_value"] = work.apply(selected_spread_line, axis=1)
    work["total_value"] = work.apply(selected_total_line, axis=1)

    work["edge_bucket"] = work["selected_edge"].apply(edge_bucket)
    work["odds_bucket"] = work["moneyline_odds_value"].apply(odds_bucket)
    work["spread_bucket"] = work["spread_value"].apply(spread_bucket)
    work["total_bucket"] = work["total_value"].apply(total_bucket)

    for col in ["edge_bucket", "spread_bucket", "odds_bucket", "total_bucket"]:
        count = (work[col] == "UNBUCKETED").sum()
        if count > 0:
            log_error(f"{league} UNBUCKETED {col}: {count}")

    return work


def build_work_file(league):
    try:
        if league == "NBA":
            path = NBA_OUTPUT / "NBA_final.csv"
        else:
            path = NCAAB_OUTPUT / "NCAAB_final.csv"

        df = safe_read(path)

        if df.empty:
            log_error(f"{league} MASTER EMPTY | {path}")
            return

        work = prepare_work_df(df, league)

        if work.empty:
            log_error(f"{league} WORK DF EMPTY AFTER PREP | {path}")
            return

        out = INTERMEDIATE_DIR / f"work_{league.lower()}.csv"
        work.to_csv(out, index=False)

        log_summary(f"{league} WORK FILE CREATED | ROWS={len(work)} | OUT={out}")

    except Exception as e:
        log_error(f"{league} BUILD WORK FILE ERROR | {e}")


def main():
    reset_logs()
    log_summary("START basketball_results_analyze.py")

    for league in ["NBA", "NCAAB"]:
        build_work_file(league)

    log_summary("END basketball_results_analyze.py")
    print("Basketball analytics preparation complete.")


if __name__ == "__main__":
    main()
