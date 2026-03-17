#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/soccer/01_soccer_results_grade.py

from datetime import datetime
from pathlib import Path
import pandas as pd

###############################################################
######################## PATH CONFIG ##########################
###############################################################

SELECT_DIR = Path("docs/win/soccer/04_select")
FINAL_SCORES_DIR = Path("docs/win/final_scores/results/soccer/final_scores")

OUTPUT_DIR = Path("docs/win/final_scores/results/soccer/graded")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "soccer_results_grade_errors.txt"
SUMMARY_LOG = ERROR_DIR / "soccer_results_grade_summary.txt"

MASTER_FILE = OUTPUT_DIR / "SOCCER_final.csv"

###############################################################
######################## LOGGING ##############################
###############################################################

def reset_logs():
    ERROR_LOG.write_text("", encoding="utf-8")
    SUMMARY_LOG.write_text("", encoding="utf-8")


def log_error(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")


def log_summary(msg):
    with open(SUMMARY_LOG, "a", encoding="utf-8") as f:
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

        if df.empty:
            log_error(f"EMPTY FILE | {path}")
            return pd.DataFrame()

        return df

    except Exception as e:
        log_error(f"READ ERROR | {path} | {e}")
        return pd.DataFrame()


def extract_date_from_select_filename(path):
    stem = Path(path).stem

    if stem.startswith("soccer_"):
        return stem.replace("soccer_", "", 1)

    return stem


def load_score_files_for_date(game_date):
    pattern = f"{game_date}_final_scores_*.csv"
    score_files = sorted(FINAL_SCORES_DIR.glob(pattern))

    if not score_files:
        log_error(f"NO SCORE FILES FOUND | DATE={game_date} | PATTERN={pattern}")
        return pd.DataFrame()

    frames = []

    for score_file in score_files:
        df = safe_read(score_file)

        if df.empty:
            continue

        needed_cols = [
            "league",
            "market",
            "game_date",
            "match_time",
            "home_team",
            "away_team",
            "away_score",
            "home_score",
        ]

        missing = [c for c in needed_cols if c not in df.columns]
        if missing:
            log_error(f"MISSING COLUMNS | {score_file} | {missing}")
            continue

        df = df[needed_cols].copy()

        df = df.rename(
            columns={
                "league": "league_scorefile",
                "market": "market_scorefile",
                "match_time": "match_time_scorefile",
            }
        )

        frames.append(df)

        log_summary(f"SCORE FILE LOADED | {score_file} | ROWS={len(df)}")

    if not frames:
        log_error(f"NO USABLE SCORE FILES | DATE={game_date}")
        return pd.DataFrame()

    scores = pd.concat(frames, ignore_index=True)

    for col in ["market_scorefile", "home_team", "away_team", "game_date"]:
        scores[col] = scores[col].astype(str).str.strip()

    scores["market_scorefile"] = scores["market_scorefile"].str.lower()

    scores = scores.drop_duplicates(
        subset=["market_scorefile", "home_team", "away_team", "game_date"],
        keep="first"
    )

    return scores

###############################################################
######################## GRADING ##############################
###############################################################

def grade_row(row):
    try:
        market = str(row.get("market_type", "")).lower().strip()
        take_bet = str(row.get("take_bet", "")).lower().strip()

        home = pd.to_numeric(row.get("home_score"), errors="coerce")
        away = pd.to_numeric(row.get("away_score"), errors="coerce")

        if pd.isna(home) or pd.isna(away):
            return "Push"

        # ================= RESULT =================
        if market == "result":

            if take_bet == "home":
                return "Win" if home > away else "Loss"

            if take_bet == "away":
                return "Win" if away > home else "Loss"

            if take_bet == "draw":
                return "Win" if home == away else "Loss"

            return "Push"

        # ================= TOTAL =================
        if market == "total":

            goals = home + away

            if take_bet == "over25":
                return "Win" if goals > 2.5 else "Loss"

            if take_bet == "under25":
                return "Win" if goals < 2.5 else "Loss"

            if take_bet == "over35":
                return "Win" if goals > 3.5 else "Loss"

            if take_bet == "under35":
                return "Win" if goals < 3.5 else "Loss"

            return "Push"

        # ================= BTTS =================
        if market == "btts":

            if take_bet == "btts_yes":
                return "Win" if (home > 0 and away > 0) else "Loss"

            if take_bet == "btts_no":
                return "Win" if (home == 0 or away == 0) else "Loss"

            return "Push"

    except Exception as e:
        log_error(f"GRADE ERROR | GAME_ID={row.get('game_id', '')} | {e}")

    return "Push"

###############################################################
######################## PROCESS ##############################
###############################################################

def process():
    select_files = sorted(SELECT_DIR.glob("soccer_*.csv"))

    if not select_files:
        log_error("NO SELECT FILES FOUND")
        return

    rows = []

    for file in select_files:
        df = safe_read(file)

        if df.empty:
            continue

        game_date = extract_date_from_select_filename(file)

        scores = load_score_files_for_date(game_date)

        if scores.empty:
            log_error(f"MISSING SCORE DATA FOR SELECT FILE | {file}")
            continue

        for col in ["market", "home_team", "away_team", "game_date"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        df["market"] = df["market"].str.lower()

        merged = df.merge(
            scores,
            left_on=["market", "home_team", "away_team", "game_date"],
            right_on=["market_scorefile", "home_team", "away_team", "game_date"],
            how="left"
        )

        merged["bet_result"] = merged.apply(grade_row, axis=1)

        out_file = OUTPUT_DIR / f"{game_date}_results_SOCCER.csv"
        merged.to_csv(out_file, index=False)

        rows.append(merged)

        matched_rows = merged["home_score"].notna().sum()
        log_summary(
            f"GRADED FILE | {out_file} | ROWS={len(merged)} | MATCHED_SCORES={matched_rows}"
        )

    if rows:
        final = pd.concat(rows, ignore_index=True)
        final.to_csv(MASTER_FILE, index=False)

        log_summary(f"MASTER FILE WRITTEN | {MASTER_FILE} | ROWS={len(final)}")

###############################################################
######################## MAIN #################################
###############################################################

def main():
    reset_logs()
    log_summary("START soccer_results_grade.py")

    process()

    log_summary("END soccer_results_grade.py")

    print("Soccer grading complete.")

if __name__ == "__main__":
    main()
