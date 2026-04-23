#!/usr/bin/env python3
# docs/win/baseball/scripts/05_final_scores/01_mlb_results_grade.py

from datetime import datetime, UTC
from pathlib import Path

import pandas as pd

###############################################################
######################## PATH CONFIG ##########################
###############################################################

SELECT_DIR  = Path("docs/win/baseball/04_select")
SCORE_DIR   = Path("docs/win/baseball/05_final_scores/results/final_scores")
OUTPUT_DIR  = Path("docs/win/baseball/05_final_scores/results/graded")
DAILY_DIR   = OUTPUT_DIR / "daily"
ERROR_DIR   = Path("docs/win/baseball/errors/05_final_scores")

ERROR_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)

GRADE_ERROR_LOG   = ERROR_DIR / "mlb_results_grade_errors.txt"
GRADE_SUMMARY_LOG = ERROR_DIR / "mlb_results_grade_summary.txt"

###############################################################
######################## OUTPUT COLUMNS #######################
###############################################################

OUTPUT_COLS = [
    "game_id",
    "sport",
    "league",
    "game_date",
    "game_time",
    "home_team",
    "away_team",
    "market_type",
    "bet_side",
    "line",
    "take_bet",
    "dk_odds_american",
    "model_prob",
    "ev",
    "kelly",
    "low_confidence",
    "final_home_score",
    "final_away_score",
    "final_total",
    "home_run_line",
    "away_run_line",
    "total",
    "bet_result",
]

###############################################################
######################## LOGGING ##############################
###############################################################

def reset_logs():
    GRADE_ERROR_LOG.write_text("", encoding="utf-8")
    GRADE_SUMMARY_LOG.write_text("", encoding="utf-8")


def log_error(msg):
    with open(GRADE_ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(UTC).isoformat()}] {msg}\n")


def log_summary(msg):
    with open(GRADE_SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(UTC).isoformat()}] {msg}\n")


###############################################################
######################## HELPERS ##############################
###############################################################

def safe_read(path):
    try:
        path = Path(path)
        if not path.exists():
            log_error(f"MISSING FILE | {path}")
            return pd.DataFrame()
        df = pd.read_csv(path, dtype=str)
        if df is None or df.empty:
            log_error(f"EMPTY FILE | {path}")
            return pd.DataFrame()
        df = df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))
        return df
    except Exception as e:
        log_error(f"READ ERROR | {path} | {e}")
        return pd.DataFrame()


def normalize_date(val):
    """Normalize date to YYYY_MM_DD format."""
    return str(val).strip().replace("-", "_")


def enforce_output_cols(df):
    """Keep only output columns, in order. Fill missing cols with empty string."""
    for col in OUTPUT_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[OUTPUT_COLS]


###############################################################
######################## OUTCOME LOGIC ########################
###############################################################

def determine_outcome(row):
    try:
        market = str(row.get("market_type", "")).strip().lower()
        side   = str(row.get("bet_side",    "")).strip().lower()

        away = float(row["final_away_score"])
        home = float(row["final_home_score"])

        if market == "moneyline":
            if away == home:
                return "Push"
            if side == "home":
                return "Win" if home > away else "Loss"
            if side == "away":
                return "Win" if away > home else "Loss"

        if market == "run_line":
            line = float(row.get("line", 0))
            diff = (home + line) - away if side == "home" else (away + line) - home
            if abs(diff) < 1e-9:
                return "Push"
            return "Win" if diff > 0 else "Loss"

        if market == "total":
            line  = float(row.get("line", 0))
            total = away + home
            if abs(total - line) < 1e-9:
                return "Push"
            if side == "over":
                return "Win" if total > line else "Loss"
            if side == "under":
                return "Win" if total < line else "Loss"

    except Exception as e:
        log_error(f"DETERMINE OUTCOME ERROR | {e}")

    return "Unknown"


###############################################################
######################## GRADING ##############################
###############################################################

def grade_league():
    # ── Load all select files ──────────────────────────────────
    select_files = sorted(SELECT_DIR.glob("*MLB*.csv"))
    if not select_files:
        log_error(f"NO SELECT FILES FOUND IN {SELECT_DIR}")
        return

    parts = []
    for f in select_files:
        df = safe_read(f)
        if not df.empty:
            df["game_date"] = df["game_date"].apply(normalize_date)
            parts.append(df)

    if not parts:
        log_error("ALL SELECT FILES EMPTY OR UNREADABLE")
        return

    all_bets = pd.concat(parts, ignore_index=True)

    if "game_id" not in all_bets.columns:
        log_error("SELECT FILES MISSING game_id COLUMN — cannot match")
        return

    # ── Load all score files ───────────────────────────────────
    score_files = sorted(SCORE_DIR.glob("*_final_scores_MLB.csv"))
    if not score_files:
        log_error(f"NO SCORE FILES FOUND IN {SCORE_DIR}")
        return

    # Build a single scores dataframe from all score files
    score_parts = []
    for sf in score_files:
        df = safe_read(sf)
        if not df.empty:
            df["game_date"] = df["game_date"].apply(normalize_date)
            score_parts.append(df)

    if not score_parts:
        log_error("ALL SCORE FILES EMPTY OR UNREADABLE")
        return

    all_scores = pd.concat(score_parts, ignore_index=True)

    if "game_id" not in all_scores.columns:
        log_error("SCORE FILES MISSING game_id COLUMN — cannot match")
        return

    # ── Merge on game_id ───────────────────────────────────────
    # Suffix _s = from scores, _b = from bets; we prefer score values for
    # score-side columns and bet values for bet-side columns.
    merged = pd.merge(
        all_bets,
        all_scores,
        on="game_id",
        how="inner",
        suffixes=("_bet", "_score"),
    )

    if merged.empty:
        log_error("MERGE EMPTY — no game_id matches between select and score files")
        return

    # Resolve duplicated columns: prefer _score for score-origin fields,
    # _bet for bet-origin fields, then drop suffixed columns.
    score_origin = {"game_date", "game_time", "home_team", "away_team",
                    "sport", "league", "final_home_score", "final_away_score",
                    "final_total", "home_run_line", "away_run_line", "total"}

    for base in score_origin:
        score_col = f"{base}_score"
        bet_col   = f"{base}_bet"
        if score_col in merged.columns:
            merged[base] = merged[score_col]
        elif bet_col in merged.columns:
            merged[base] = merged[bet_col]

    # For any remaining _bet / _score duplicates not in score_origin, keep _bet
    for col in list(merged.columns):
        if col.endswith("_bet"):
            base = col[:-4]
            if base not in merged.columns:
                merged[base] = merged[col]
        elif col.endswith("_score"):
            base = col[:-6]
            if base not in merged.columns:
                merged[base] = merged[col]

    merged = merged.drop(
        columns=[c for c in merged.columns if c.endswith("_bet") or c.endswith("_score")],
        errors="ignore",
    )

    # ── Grade each row ─────────────────────────────────────────
    merged["bet_result"] = merged.apply(determine_outcome, axis=1)

    # ── Deduplicate ────────────────────────────────────────────
    key_cols = [c for c in ["game_id", "market_type", "bet_side"] if c in merged.columns]
    merged = merged.drop_duplicates(subset=key_cols, keep="last")

    # ── Write master output ────────────────────────────────────
    final = enforce_output_cols(merged)
    master_path = OUTPUT_DIR / "MLB_final.csv"
    final.to_csv(master_path, index=False)
    log_summary(f"MLB MASTER BUILT | ROWS={len(final)} | OUT={master_path}")

    # ── Write daily outputs ────────────────────────────────────
    if "game_date" in merged.columns:
        for date_val, group in merged.groupby("game_date"):
            date_str = normalize_date(date_val)   # ensure YYYY_MM_DD
            daily_df = enforce_output_cols(group.copy())
            daily_path = DAILY_DIR / f"{date_str}_MLB_final.csv"
            daily_df.to_csv(daily_path, index=False)
            result_counts = group["bet_result"].astype(str).value_counts().to_dict()
            log_summary(f"MLB DAILY | DATE={date_str} | ROWS={len(daily_df)} | RESULTS={result_counts}")
    else:
        log_error("game_date column missing from merged output — daily files not written")


###############################################################
######################## MAIN #################################
###############################################################

def main():
    reset_logs()
    log_summary("START 01_mlb_results_grade.py")
    grade_league()
    log_summary("END 01_mlb_results_grade.py")
    print("MLB grading complete.")


if __name__ == "__main__":
    main()
