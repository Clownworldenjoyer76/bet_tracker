#!/usr/bin/env python3
# docs/win/basketball/scripts/02_juice/apply_spread_juice.py

import pandas as pd
from pathlib import Path
import math
from datetime import datetime
import traceback
import sys

# =========================
# LOGGER UTILITY
# =========================

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. EXHAUSTIVE LOG (TXT)
    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

    # 2. CONDENSED SUMMARY (TXT)
    if df is not None and isinstance(df, pd.DataFrame):
        summary_path = log_path.parent / "condensed_summary.txt"
        
        play_cols = [c for c in ['home_play', 'away_play', 'over_play', 'under_play'] if c in df.columns]
        
        if play_cols:
            signals = df[df[play_cols].any(axis=1)].copy()
            
            if not signals.empty:
                with open(summary_path, "a") as f:
                    f.write(f"\n--- BETTING SIGNALS: {ts} ---\n")
                    base_cols = ['game_date', 'home_team', 'away_team']
                    edge_cols = [c for c in df.columns if 'edge_pct' in c]
                    
                    final_cols = [c for c in base_cols + edge_cols if c in signals.columns]
                    f.write(signals[final_cols].to_string(index=False))
                    f.write("\n" + "="*30 + "\n")

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/01_merge")
OUTPUT_DIR = Path("docs/win/basketball/02_juice")
ERROR_DIR = Path("docs/win/basketball/errors/02_juice")

NBA_CONFIG = Path("config/basketball/nba/nba_spreads_juice.csv")
NCAAB_CONFIG = Path("config/basketball/ncaab/ncaab_spreads_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "apply_spread_juice.txt"

def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


def american_to_decimal(a):
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def decimal_to_american(d):
    if not math.isfinite(d) or d <= 1:
        return ""
    if d >= 2:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


def apply_nba(df):

    jt = pd.read_csv(NBA_CONFIG)

    def process(row, side):

        spread = float(row[f"{side}_spread"])
        odds = float(row[f"{side}_acceptable_spread_american"])

        fav_ud = "favorite" if spread < 0 else "underdog"

        band = jt[
            (jt["band_min"] <= abs(spread)) &
            (abs(spread) <= jt["band_max"]) &
            (jt["fav_ud"] == fav_ud) &
            (jt["venue"] == side)
        ]

        extra = band.iloc[0]["extra_juice"] if not band.empty else 0.0
        if not math.isfinite(extra):
            extra = 0.0

        base_decimal = american_to_decimal(odds)
        final_decimal = base_decimal * (1 + extra)

        return final_decimal, decimal_to_american(final_decimal)

    for side in ["home", "away"]:
        df[[f"{side}_spread_juice_decimal",
            f"{side}_spread_juice_odds"]] = \
            df.apply(lambda r: process(r, side),
                     axis=1,
                     result_type="expand")

    return df


def apply_ncaab(df):

    jt = pd.read_csv(NCAAB_CONFIG)

    def process(row, side):

        spread = float(row[f"{side}_spread"])
        odds = float(row[f"{side}_acceptable_spread_american"])

        match = jt[jt["spread"] == spread]

        extra = match.iloc[0]["extra_juice"] if not match.empty else 0.0
        if not math.isfinite(extra):
            extra = 0.0

        base_decimal = american_to_decimal(odds)
        final_decimal = base_decimal * (1 + extra)

        return final_decimal, decimal_to_american(final_decimal)

    for side in ["home", "away"]:
        df[[f"{side}_spread_juice_decimal",
            f"{side}_spread_juice_odds"]] = \
            df.apply(lambda r: process(r, side),
                     axis=1,
                     result_type="expand")

    return df


def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(f"=== APPLY SPREAD JUICE START {datetime.utcnow().isoformat()}Z ===\n")

    try:
        files_found = 0

        for f in INPUT_DIR.iterdir():

            name = f.name

            if name.endswith("_NBA_spread.csv"):
                df = pd.read_csv(f)
                df = apply_nba(df)
                df.to_csv(OUTPUT_DIR / name, index=False)
                log(f"Processed NBA file: {name}")
                audit(ERROR_LOG, "JUICE_SPREAD_NBA", "SUCCESS", msg=f"Applied NBA Spread Juice to {name}", df=df)
                files_found += 1

            elif name.endswith("_NCAAB_spread.csv"):
                df = pd.read_csv(f)
                df = apply_ncaab(df)
                df.to_csv(OUTPUT_DIR / name, index=False)
                log(f"Processed NCAAB file: {name}")
                audit(ERROR_LOG, "JUICE_SPREAD_NCAAB", "SUCCESS", msg=f"Applied NCAAB Spread Juice to {name}", df=df)
                files_found += 1

        log(f"Total files processed: {files_found}")
        log("=== APPLY SPREAD JUICE END ===")

    except Exception as e:
        log("=== ERROR ===")
        log(str(e))
        log(traceback.format_exc())
        audit(ERROR_LOG, "JUICE_SPREAD_CRITICAL", "FAILED", msg=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
