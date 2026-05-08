#!/usr/bin/env python3
# docs/win/soccer/scripts/05_final_scores/02_soccer_results_analyze.py

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback

import pandas as pd


# =========================
# PATHS
# =========================

OUTPUT_DIR = Path("docs/win/soccer/05_final_scores/results/graded")
INTERMEDIATE_DIR = Path("docs/win/soccer/05_final_scores/intermediate")
ERROR_DIR = Path("docs/win/soccer/05_final_scores/errors")

INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "soccer_results_analyze_errors.txt"
SUMMARY_LOG = ERROR_DIR / "soccer_results_analyze_summary.txt"

MASTER_FILE = OUTPUT_DIR / "SOCCER_final.csv"
WORK_FILE = INTERMEDIATE_DIR / "work_soccer.csv"


# =========================
# REQUIRED HEADERS
# =========================

REQUIRED_COLUMNS = [
    "game_id",
    "sport",
    "league",
    "match_date",
    "match_time",
    "home_team",
    "away_team",
    "market",
    "side",
    "odds",
    "ev",
    "kelly",
    "game_date",
    "league_lower",
    "market_type",
    "take_bet",
    "odds_american",
    "edge_pct",
    "home_score",
    "away_score",
    "bet_result",
]


# =========================
# LOGGING
# =========================

def reset_logs() -> None:
    ERROR_LOG.write_text("", encoding="utf-8")
    SUMMARY_LOG.write_text("", encoding="utf-8")


def log_error(msg: str) -> None:
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def log_summary(msg: str) -> None:
    with open(SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


# =========================
# HELPERS
# =========================

def safe_read_csv(path: Path) -> pd.DataFrame:
    try:
        if not path.exists():
            log_error(f"MASTER FILE MISSING | {path}")
            return pd.DataFrame()

        df = pd.read_csv(path)

        if df.empty:
            log_error(f"MASTER FILE EMPTY | {path}")
            return pd.DataFrame()

        return df

    except Exception as e:
        log_error(f"READ ERROR | {path} | {e}")
        log_error(traceback.format_exc())
        return pd.DataFrame()


def validate_headers(df: pd.DataFrame, required: list[str], path: Path) -> bool:
    missing = [c for c in required if c not in df.columns]

    if missing:
        log_error(f"MISSING HEADERS | {path}")
        log_error(f"Missing: {missing}")
        log_error(f"Available: {list(df.columns)}")
        return False

    return True


def clean_text_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def edge_bucket(v) -> str:
    v = pd.to_numeric(v, errors="coerce")

    if pd.isna(v):
        return "no_edge"
    if v < 0.01:
        return "0_to_0.01"
    if v < 0.02:
        return "0.01_to_0.02"
    if v < 0.03:
        return "0.02_to_0.03"
    if v < 0.05:
        return "0.03_to_0.05"
    return "0.05_plus"


def odds_bucket(v) -> str:
    v = pd.to_numeric(v, errors="coerce")

    if pd.isna(v):
        return "no_odds"

    # Soccer select odds are decimal in the graded file.
    if 1 <= v <= 20:
        if v < 1.50:
            return "decimal_under_1.50"
        if v < 1.75:
            return "decimal_1.50_to_1.74"
        if v < 2.00:
            return "decimal_1.75_to_1.99"
        if v < 2.50:
            return "decimal_2.00_to_2.49"
        if v < 3.00:
            return "decimal_2.50_to_2.99"
        return "decimal_3.00_plus"

    # Fallback if an actual American-odds column is ever passed here.
    if v < -150:
        return "american_minus_150_or_lower"
    if v < -110:
        return "american_minus_149_to_minus_110"
    if v < 100:
        return "american_minus_109_to_plus_100"
    if v < 150:
        return "american_plus_101_to_plus_150"
    return "american_plus_151_or_higher"


# =========================
# PREPARE
# =========================

def prepare() -> None:
    df = safe_read_csv(MASTER_FILE)

    if df.empty:
        return

    if not validate_headers(df, REQUIRED_COLUMNS, MASTER_FILE):
        return

    for col in [
        "game_id",
        "sport",
        "league",
        "match_date",
        "match_time",
        "home_team",
        "away_team",
        "market",
        "side",
        "game_date",
        "league_lower",
        "market_type",
        "take_bet",
        "bet_result",
    ]:
        df[col] = clean_text_series(df[col])

    df["selected_edge"] = pd.to_numeric(df["edge_pct"], errors="coerce")
    df["selected_odds"] = pd.to_numeric(df["odds_american"], errors="coerce")

    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")

    df["edge_bucket"] = df["selected_edge"].apply(edge_bucket)
    df["odds_bucket"] = df["selected_odds"].apply(odds_bucket)

    if "score_league" in df.columns:
        df["market_scorefile"] = df["score_league"].astype(str).str.strip()
    elif "market_scorefile" not in df.columns:
        df["market_scorefile"] = ""

    df.to_csv(WORK_FILE, index=False)

    log_summary(f"WORK FILE CREATED | {WORK_FILE} | rows={len(df)}")
    log_summary(f"market_type counts: {df['market_type'].value_counts(dropna=False).to_dict()}")
    log_summary(f"bet_result counts: {df['bet_result'].value_counts(dropna=False).to_dict()}")
    log_summary(f"edge_bucket counts: {df['edge_bucket'].value_counts(dropna=False).to_dict()}")
    log_summary(f"odds_bucket counts: {df['odds_bucket'].value_counts(dropna=False).to_dict()}")


# =========================
# MAIN
# =========================

def main() -> None:
    reset_logs()
    log_summary(f"=== START 02_soccer_results_analyze.py {datetime.now().isoformat()} ===")
    prepare()
    log_summary(f"=== END 02_soccer_results_analyze.py {datetime.now().isoformat()} ===")
    print("Soccer analytics preparation complete.")


if __name__ == "__main__":
    main()
