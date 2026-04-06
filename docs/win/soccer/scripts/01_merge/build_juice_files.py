#!/usr/bin/env python3
# docs/win/soccer/scripts/01_merge/build_juice_files.py

import glob
import math
import traceback
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from scipy.stats import poisson

INPUT_DIR  = Path("docs/win/soccer/01_merge")
OUTPUT_DIR = INPUT_DIR / "01_merguiced"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR  = Path("docs/win/soccer/errors/01_merge")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "build_juice_files_log.txt"

LEAGUES = ["epl", "laliga", "ligue1", "bundesliga", "seriea", "mls"]

BASE_COLS = [
    "game_id", "sport", "league", "match_date", "match_time",
    "home_team", "away_team",
    "home_prob", "draw_prob", "away_prob",
    "home_xg", "away_xg", "expected_total_goals",
]

MATCH_ODDS_COLS  = BASE_COLS + ["dk_home_decimal", "dk_draw_decimal", "dk_away_decimal"]
TOTAL_25_COLS    = BASE_COLS + ["dk_over25_decimal", "dk_under25_decimal"]
TOTAL_35_COLS    = BASE_COLS + ["dk_over35_decimal", "dk_under35_decimal"]
BTTS_COLS        = BASE_COLS + ["btts_yes", "btts_no"]


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")


def coerce_numeric(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def validate_schema(df, required, file_path):
    missing = [c for c in required if c not in df.columns]
    if missing:
        log(f"SCHEMA ERROR: {file_path} missing: {missing}")
        return False
    return True


def parse_stem(stem):
    """Returns (date, league, market) from filename stem."""
    for lg in LEAGUES:
        for market in ["match_odds", "total_25", "total_35", "btts"]:
            suffix = f"_{lg}_{market}"
            if stem.endswith(suffix):
                date = stem[: -len(suffix)]
                return date, lg, market
    return None, None, None


# =========================
# MATCH ODDS
# =========================

def process_match_odds(file_path):
    df = pd.read_csv(file_path)
    if df.empty:
        log(f"EMPTY: {file_path}")
        return
    if not validate_schema(df, MATCH_ODDS_COLS, file_path):
        return

    coerce_numeric(df, [
        "home_prob", "draw_prob", "away_prob",
        "dk_home_decimal", "dk_draw_decimal", "dk_away_decimal",
    ])

    # Fair decimals derived directly from model probs
    df["fair_home_decimal"] = df["home_prob"].apply(
        lambda x: 1 / x if pd.notna(x) and x > 0 else None
    )
    df["fair_draw_decimal"] = df["draw_prob"].apply(
        lambda x: 1 / x if pd.notna(x) and x > 0 else None
    )
    df["fair_away_decimal"] = df["away_prob"].apply(
        lambda x: 1 / x if pd.notna(x) and x > 0 else None
    )

    date, league, market = parse_stem(Path(file_path).stem)
    if not date:
        log(f"FILENAME ERROR: {file_path}")
        return

    out = OUTPUT_DIR / f"{date}_{league}_match_odds.csv"
    df.to_csv(out, index=False)
    log(f"WROTE {out} ({len(df)} rows)")


# =========================
# TOTALS (Poisson)
# =========================

def compute_total_probs(df, total_line, file_path):
    over_probs  = []
    under_probs = []

    for i, r in df.iterrows():
        lam = r["expected_total_goals"]

        if pd.isna(lam) or lam <= 0:
            log(f"ROW ISSUE: {file_path} idx={i} invalid expected_total_goals")
            over_probs.append(None)
            under_probs.append(None)
            continue

        if total_line % 1 == 0:
            log(f"WHOLE NUMBER TOTAL: {file_path} idx={i} total={total_line} — skipping")
            over_probs.append(None)
            under_probs.append(None)
            continue

        k       = math.floor(total_line)
        p_under = poisson.cdf(k, lam)
        p_over  = 1 - p_under

        under_probs.append(1 / p_under if p_under > 0 else None)
        over_probs.append(1 / p_over   if p_over  > 0 else None)

    return over_probs, under_probs


def process_total(file_path, total_line, over_col, under_col):
    df = pd.read_csv(file_path)
    if df.empty:
        log(f"EMPTY: {file_path}")
        return

    required = BASE_COLS + [over_col, under_col]
    if not validate_schema(df, required, file_path):
        return

    coerce_numeric(df, ["expected_total_goals", over_col, under_col])

    over_probs, under_probs = compute_total_probs(df, total_line, file_path)

    df["fair_over_decimal"]  = over_probs
    df["fair_under_decimal"] = under_probs

    date, league, market = parse_stem(Path(file_path).stem)
    if not date:
        log(f"FILENAME ERROR: {file_path}")
        return

    out = OUTPUT_DIR / f"{date}_{league}_{market}.csv"
    df.to_csv(out, index=False)
    log(f"WROTE {out} ({len(df)} rows)")


# =========================
# BTTS
# =========================

def process_btts(file_path):
    df = pd.read_csv(file_path)
    if df.empty:
        log(f"EMPTY: {file_path}")
        return
    if not validate_schema(df, BTTS_COLS, file_path):
        return

    coerce_numeric(df, ["home_prob", "draw_prob", "away_prob", "btts_yes", "btts_no"])

    # Fair BTTS probs — implied from sportsbook with vig removed
    def implied_prob(decimal):
        return 1 / decimal if pd.notna(decimal) and decimal > 0 else None

    rows_yes = df["btts_yes"].apply(implied_prob)
    rows_no  = df["btts_no"].apply(implied_prob)

    fair_yes = []
    fair_no  = []

    for y, n in zip(rows_yes, rows_no):
        if y is not None and n is not None and (y + n) > 0:
            total = y + n
            fair_yes.append(1 / (y / total))
            fair_no.append(1 / (n / total))
        else:
            fair_yes.append(None)
            fair_no.append(None)

    df["fair_btts_yes_decimal"] = fair_yes
    df["fair_btts_no_decimal"]  = fair_no

    date, league, market = parse_stem(Path(file_path).stem)
    if not date:
        log(f"FILENAME ERROR: {file_path}")
        return

    out = OUTPUT_DIR / f"{date}_{league}_btts.csv"
    df.to_csv(out, index=False)
    log(f"WROTE {out} ({len(df)} rows)")


# =========================
# MAIN
# =========================

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== build_juice_files RUN {datetime.now(timezone.utc).isoformat()} ===\n")

    try:
        for f in sorted(INPUT_DIR.glob("*_match_odds.csv")):
            process_match_odds(str(f))

        for f in sorted(INPUT_DIR.glob("*_total_25.csv")):
            process_total(str(f), 2.5, "dk_over25_decimal", "dk_under25_decimal")

        for f in sorted(INPUT_DIR.glob("*_total_35.csv")):
            process_total(str(f), 3.5, "dk_over35_decimal", "dk_under35_decimal")

        for f in sorted(INPUT_DIR.glob("*_btts.csv")):
            process_btts(str(f))

        log("COMPLETE")

    except Exception as e:
        log(f"FATAL: {e}\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
