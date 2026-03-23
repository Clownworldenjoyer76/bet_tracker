#!/usr/bin/env python3
# docs/win/basketball/scripts/02_juice/apply_total_juice.py

import pandas as pd
from pathlib import Path
import math
from datetime import datetime, UTC
import traceback
import sys

# =========================
# LOGGER UTILITY
# =========================

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
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
# PATHS (UPDATED)
# =========================

INPUT_DIR = Path("docs/win/basketball/01_merge/01_merguiced")
OUTPUT_DIR = Path("docs/win/basketball/02_juice")
ERROR_DIR = Path("docs/win/basketball/errors/02_juice")

NBA_CONFIG = Path("config/basketball/nba/nba_totals_juice.csv")
NCAAB_CONFIG = Path("config/basketball/ncaab/ncaab_totals_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "apply_total_juice.txt"


# =========================
# CLEAN OLD OUTPUTS
# =========================

for f in OUTPUT_DIR.glob("*_NBA_total.csv"):
    f.unlink(missing_ok=True)

for f in OUTPUT_DIR.glob("*_NCAAB_total.csv"):
    f.unlink(missing_ok=True)


def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(UTC).isoformat()} | {msg}\n")


# =========================
# CONFIG LOAD
# =========================

try:
    NBA_JUICE = pd.read_csv(NBA_CONFIG)
    NCAAB_JUICE = pd.read_csv(NCAAB_CONFIG)
except FileNotFoundError as e:
    raise SystemExit(f"ERROR: Missing juice config file — {e}") from e

NBA_JUICE["band_min"] = pd.to_numeric(NBA_JUICE["band_min"], errors="coerce")
NBA_JUICE["band_max"] = pd.to_numeric(NBA_JUICE["band_max"], errors="coerce")
NBA_JUICE["extra_juice"] = pd.to_numeric(NBA_JUICE["extra_juice"], errors="coerce")

NCAAB_JUICE["over_under"] = pd.to_numeric(NCAAB_JUICE["over_under"], errors="coerce")
NCAAB_JUICE["extra_juice"] = pd.to_numeric(NCAAB_JUICE["extra_juice"], errors="coerce")


# =========================
# ODDS CONVERSION
# =========================

def decimal_to_american(d):

    if d is None or not math.isfinite(d) or d <= 1:
        return ""

    if d >= 2:
        return f"+{int(round((d - 1) * 100))}"

    return f"-{int(round(100 / (d - 1)))}"


# =========================
# VALIDATION
# =========================

def validate_columns(df, cols):

    missing = [c for c in cols if c not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")


# =========================
# NBA PROCESSING
# =========================

def apply_nba(df):

    validate_columns(df, ["total", "acceptable_over", "acceptable_under"])

    def process(row, side):

        total = pd.to_numeric(row.get("total"), errors="coerce")
        if pd.isna(total):
            return None, ""

        base_col = "acceptable_over" if side == "over" else "acceptable_under"
        base_decimal = pd.to_numeric(row.get(base_col), errors="coerce")

        if pd.isna(base_decimal) or not math.isfinite(base_decimal) or base_decimal <= 1:
            return None, ""

        band = NBA_JUICE[
            (NBA_JUICE["band_min"] <= total) &
            (total <= NBA_JUICE["band_max"]) &
            (NBA_JUICE["side"] == side)
        ]

        extra = band.iloc[0]["extra_juice"] if not band.empty else 0.0

        if pd.isna(extra) or not math.isfinite(extra):
            extra = 0.0

        final_decimal = base_decimal * (1 + extra)

        if not math.isfinite(final_decimal) or final_decimal <= 1:
            return None, ""

        return final_decimal, decimal_to_american(final_decimal)

    df[["total_over_juice_decimal", "total_over_juice_odds"]] = \
        df.apply(lambda r: process(r, "over"), axis=1, result_type="expand")

    df[["total_under_juice_decimal", "total_under_juice_odds"]] = \
        df.apply(lambda r: process(r, "under"), axis=1, result_type="expand")

    df["acceptable_over"] = df["total_over_juice_decimal"]
    df["acceptable_under"] = df["total_under_juice_decimal"]

    return df


# =========================
# NCAAB PROCESSING (FIXED)
# =========================

def apply_ncaab(df):

    validate_columns(df, ["total", "acceptable_over", "acceptable_under"])

    def process(row, side):

        total = pd.to_numeric(row.get("total"), errors="coerce")
        if pd.isna(total):
            return None, ""

        base_col = "acceptable_over" if side == "over" else "acceptable_under"
        base_decimal = pd.to_numeric(row.get(base_col), errors="coerce")

        if pd.isna(base_decimal) or not math.isfinite(base_decimal) or base_decimal <= 1:
            return None, ""

        jt_side = NCAAB_JUICE[NCAAB_JUICE["side"] == side].copy()

        if jt_side.empty:
            extra = 0.0
        else:
            jt_side["diff"] = (jt_side["over_under"] - total).abs()
            nearest = jt_side.loc[jt_side["diff"].idxmin()]
            extra = nearest["extra_juice"]

        if pd.isna(extra) or not math.isfinite(extra):
            extra = 0.0

        final_decimal = base_decimal * (1 + extra)

        if not math.isfinite(final_decimal) or final_decimal <= 1:
            return None, ""

        return final_decimal, decimal_to_american(final_decimal)

    df[["total_over_juice_decimal", "total_over_juice_odds"]] = \
        df.apply(lambda r: process(r, "over"), axis=1, result_type="expand")

    df[["total_under_juice_decimal", "total_under_juice_odds"]] = \
        df.apply(lambda r: process(r, "under"), axis=1, result_type="expand")

    df["acceptable_over"] = df["total_over_juice_decimal"]
    df["acceptable_under"] = df["total_under_juice_decimal"]

    return df


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(f"=== APPLY TOTAL JUICE START {datetime.now(UTC).isoformat()}Z ===\n")

    try:

        files_found = 0

        for f in INPUT_DIR.iterdir():

            name = f.name

            if name.endswith("_NBA_total.csv"):

                df = pd.read_csv(f)
                df = apply_nba(df)

                df.to_csv(OUTPUT_DIR / name, index=False)

                log(f"Processed NBA file: {name}")

                audit(ERROR_LOG, "JUICE_TOTAL_NBA", "SUCCESS",
                      msg=f"Applied NBA Totals Juice to {name}", df=df)

                files_found += 1


            elif name.endswith("_NCAAB_total.csv"):

                df = pd.read_csv(f)
                df = apply_ncaab(df)

                df.to_csv(OUTPUT_DIR / name, index=False)

                log(f"Processed NCAAB file: {name}")

                audit(ERROR_LOG, "JUICE_TOTAL_NCAAB", "SUCCESS",
                      msg=f"Applied NCAAB Totals Juice to {name}", df=df)

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