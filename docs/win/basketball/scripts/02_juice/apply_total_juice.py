#!/usr/bin/env python3
# docs/win/basketball/scripts/02_juice/apply_total_juice.py

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

    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg:
            f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/01_merge")
OUTPUT_DIR = Path("docs/win/basketball/02_juice")
ERROR_DIR = Path("docs/win/basketball/errors/02_juice")

NBA_CONFIG = Path("config/basketball/nba/nba_totals_juice.csv")
NCAAB_CONFIG = Path("config/basketball/ncaab/ncaab_totals_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "apply_total_juice.txt"


def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


# =========================
# ODDS CONVERSION
# =========================

def american_to_decimal(a):
    a = float(a)
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def decimal_to_american(d):
    if not math.isfinite(d) or d <= 1:
        return ""
    if d >= 2:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


# =========================
# SAFE COLUMN RESOLUTION
# =========================

def resolve_total_odds(row, side):

    # preferred column
    col1 = f"acceptable_total_{side}_american"

    # fallback column
    col2 = f"dk_total_{side}_american"

    if col1 in row and pd.notna(row[col1]):
        return float(row[col1])

    if col2 in row and pd.notna(row[col2]):
        return float(row[col2])

    raise KeyError(f"Missing total odds column for {side}")


# =========================
# NBA PROCESSING
# =========================

def apply_nba(df):

    jt = pd.read_csv(NBA_CONFIG)

    jt["band_min"] = pd.to_numeric(jt["band_min"], errors="coerce")
    jt["band_max"] = pd.to_numeric(jt["band_max"], errors="coerce")

    def process(row, side):

        total = float(row["total"])
        odds = resolve_total_odds(row, side)

        band = jt[
            (jt["band_min"] <= total) &
            (total <= jt["band_max"]) &
            (jt["side"] == side)
        ]

        extra = band.iloc[0]["extra_juice"] if not band.empty else 0.0
        if not math.isfinite(extra):
            extra = 0.0

        base_decimal = american_to_decimal(odds)
        final_decimal = base_decimal * (1 + extra)

        return final_decimal, decimal_to_american(final_decimal)

    df[["total_over_juice_decimal", "total_over_juice_odds"]] = \
        df.apply(lambda r: process(r, "over"), axis=1, result_type="expand")

    df[["total_under_juice_decimal", "total_under_juice_odds"]] = \
        df.apply(lambda r: process(r, "under"), axis=1, result_type="expand")

    return df


# =========================
# NCAAB PROCESSING
# =========================

def apply_ncaab(df):

    jt = pd.read_csv(NCAAB_CONFIG)

    def process(row, side):

        total = float(row["total"])
        odds = resolve_total_odds(row, side)

        match = jt[
            (jt["over_under"] == total) &
            (jt["side"] == side)
        ]

        extra = match.iloc[0]["extra_juice"] if not match.empty else 0.0
        if not math.isfinite(extra):
            extra = 0.0

        base_decimal = american_to_decimal(odds)
        final_decimal = base_decimal * (1 + extra)

        return final_decimal, decimal_to_american(final_decimal)

    df[["total_over_juice_decimal", "total_over_juice_odds"]] = \
        df.apply(lambda r: process(r, "over"), axis=1, result_type="expand")

    df[["total_under_juice_decimal", "total_under_juice_odds"]] = \
        df.apply(lambda r: process(r, "under"), axis=1, result_type="expand")

    return df


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(f"=== APPLY TOTAL JUICE START {datetime.utcnow().isoformat()}Z ===\n")

    try:

        files_found = 0

        for f in INPUT_DIR.iterdir():

            name = f.name

            if name.endswith("_NBA_total.csv"):
                df = pd.read_csv(f)
                df = apply_nba(df)
                df.to_csv(OUTPUT_DIR / name, index=False)

                log(f"Processed NBA file: {name}")
                audit(ERROR_LOG, "JUICE_TOTAL_NBA", "SUCCESS", msg=f"Applied NBA Totals Juice to {name}", df=df)
                files_found += 1

            elif name.endswith("_NCAAB_total.csv"):
                df = pd.read_csv(f)
                df = apply_ncaab(df)
                df.to_csv(OUTPUT_DIR / name, index=False)

                log(f"Processed NCAAB file: {name}")
                audit(ERROR_LOG, "JUICE_TOTAL_NCAAB", "SUCCESS", msg=f"Applied NCAAB Totals Juice to {name}", df=df)
                files_found += 1

        log(f"Total files processed: {files_found}")
        log("=== APPLY TOTAL JUICE END ===")

    except Exception as e:

        log("=== ERROR ===")
        log(str(e))
        log(traceback.format_exc())

        audit(ERROR_LOG, "JUICE_TOTAL_CRITICAL", "FAILED", msg=str(e))

        sys.exit(1)


if __name__ == "__main__":
    main()
