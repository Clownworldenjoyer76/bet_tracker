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
    "game_id", "sport", "league", "game_date", "game_time",
    "home_team", "away_team", "market_type", "bet_side", "line",
    "take_bet", "dk_odds_american", "model_prob", "ev", "kelly",
    "low_confidence", "final_home_score", "final_away_score",
    "final_total", "home_run_line", "away_run_line", "total", "bet_result",
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
    return str(val).strip().replace("-", "_")

def clean_game_id(series):
    return series.fillna("").astype(str).str.strip().str.split(".").str[0]

def enforce_output_cols(df):
    for col in OUTPUT_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[OUTPUT_COLS].copy()

def resolve_suffixed_cols(merged):
    score_origin = {
        "game_date", "game_time", "home_team", "away_team",
        "sport", "league", "final_home_score", "final_away_score",
        "final_total", "home_run_line", "away_run_line", "total"
    }
    for base in score_origin:
        if f"{base}_score" in merged.columns:
            merged[base] = merged[f"{base}_score"]
        elif f"{base}_bet" in merged.columns:
            merged[base] = merged[f"{base}_bet"]
    for col in list(merged.columns):
        if col.endswith("_bet"):
            base = col[:-4]
            if base not in merged.columns:
                merged[base] = merged[col]
        elif col.endswith("_score"):
            base = col[:-6]
            if base not in merged.columns:
                merged[base] = merged[col]
    # Only drop columns that were created by the merge suffix (_bet/_score appended by pandas)
    # Do NOT drop columns whose natural name ends in _score (e.g. final_away_score, final_home_score)
    suffixed = [c for c in merged.columns if
                (c.endswith("_bet") and c[:-4] in merged.columns) or
                (c.endswith("_score") and c[:-6] in merged.columns)]
    merged = merged.drop(columns=suffixed, errors="ignore")
    return merged

###############################################################
######################## OUTCOME LOGIC ########################
###############################################################

def determine_outcome(row):
    try:
        market = str(row.get("market_type", "")).strip().lower()
        side   = str(row.get("bet_side",    "")).strip().lower()
        away   = float(row["final_away_score"])
        home   = float(row["final_home_score"])

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
    # ── Load select files ──────────────────────────────────────
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

    # ── Load score files ───────────────────────────────────────
    score_files = sorted(SCORE_DIR.glob("*_final_scores_MLB.csv"))
    if not score_files:
        log_error(f"NO SCORE FILES FOUND IN {SCORE_DIR}")
        return

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

    # ── Normalize game_id ──────────────────────────────────────
    if "game_id" in all_bets.columns:
        all_bets["game_id"] = clean_game_id(all_bets["game_id"])
    if "game_id" in all_scores.columns:
        all_scores["game_id"] = clean_game_id(all_scores["game_id"])

    # ── Merge strategy ─────────────────────────────────────────
    # Primary: game_id — only where both sides have a non-empty game_id
    # Fallback: game_date + home_team + away_team for score rows with no game_id
    merged_parts = []

    scores_with_id = all_scores[
        all_scores.get("game_id", pd.Series(dtype=str)).ne("")
    ] if "game_id" in all_scores.columns else pd.DataFrame()

    scores_no_id = all_scores[
        all_scores.get("game_id", pd.Series(dtype=str)).eq("")
    ] if "game_id" in all_scores.columns else all_scores

    bets_with_id = all_bets[
        all_bets.get("game_id", pd.Series(dtype=str)).ne("")
    ] if "game_id" in all_bets.columns else pd.DataFrame()

    # Primary merge on game_id
    if not scores_with_id.empty and not bets_with_id.empty:
        m1 = pd.merge(
            bets_with_id, scores_with_id,
            on="game_id", how="inner",
            suffixes=("_bet", "_score")
        )
        if not m1.empty:
            merged_parts.append(m1)
            log_summary(f"MERGED ON game_id | rows={len(m1)}")

    # Fallback merge on date + teams
    if not scores_no_id.empty:
        m2 = pd.merge(
            all_bets, scores_no_id,
            on=["game_date", "home_team", "away_team"],
            how="inner",
            suffixes=("_bet", "_score")
        )
        if not m2.empty:
            if "game_id_bet" in m2.columns:
                m2["game_id"] = m2["game_id_bet"]
            merged_parts.append(m2)
            log_summary(f"MERGED ON date+teams fallback | rows={len(m2)}")

    if not merged_parts:
        log_error("MERGE EMPTY — no matches on game_id or game_date+home_team+away_team")
        return

    merged = pd.concat(merged_parts, ignore_index=True)
    merged = resolve_suffixed_cols(merged)

    # ── Grade ──────────────────────────────────────────────────
    merged["bet_result"] = merged.apply(determine_outcome, axis=1)

    # ── Deduplicate ────────────────────────────────────────────
    key_cols = [c for c in ["game_id", "market_type", "bet_side"] if c in merged.columns]
    merged = merged.drop_duplicates(subset=key_cols, keep="last")

    # ── Master output ──────────────────────────────────────────
    final = enforce_output_cols(merged)
    master_path = OUTPUT_DIR / "MLB_final.csv"
    final.to_csv(master_path, index=False)
    log_summary(f"MLB MASTER BUILT | ROWS={len(final)} | OUT={master_path}")

    # ── Daily outputs ──────────────────────────────────────────
    for date_val, group in merged.groupby("game_date"):
        date_str   = normalize_date(date_val)
        daily_df   = enforce_output_cols(group.copy())
        daily_path = DAILY_DIR / f"{date_str}_MLB_final.csv"
        daily_df.to_csv(daily_path, index=False)
        result_counts = group["bet_result"].value_counts().to_dict()
        log_summary(f"MLB DAILY | DATE={date_str} | ROWS={len(daily_df)} | RESULTS={result_counts}")

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
