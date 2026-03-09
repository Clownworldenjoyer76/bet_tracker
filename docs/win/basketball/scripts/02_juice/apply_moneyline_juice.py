#!/usr/bin/env python3
# docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py

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

    with open(log_path, "a", encoding="utf-8") as f:
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

NBA_CONFIG = Path("config/basketball/nba/nba_ml_juice.csv")
NCAAB_CONFIG = Path("config/basketball/ncaab/ncaab_ml_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "apply_moneyline_juice.txt"


# =========================
# HELPERS
# =========================

def validate_columns(df, required_cols, file_name=""):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{file_name} missing required columns: {missing}")


def normalize_american_value(val):
    if pd.isna(val):
        return None
    text = str(val).strip().replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except Exception:
        return None


def american_to_decimal(a):
    a = normalize_american_value(a)
    if a is None or a == 0:
        return None
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def decimal_to_american(d):
    try:
        d = float(d)
    except Exception:
        return ""
    if not math.isfinite(d) or d <= 1:
        return ""
    if d >= 2:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


def safe_decimal(val, fallback=1.01):
    try:
        val = float(val)
    except Exception:
        return fallback
    if not math.isfinite(val) or val <= 1:
        return fallback
    return val


def safe_extra(val):
    try:
        val = float(val)
    except Exception:
        return 0.0
    if not math.isfinite(val):
        return 0.0
    return val


def atomic_write_csv(df, output_path):
    tmp_path = output_path.with_suffix(".tmp")
    df.to_csv(tmp_path, index=False)
    tmp_path.replace(output_path)


def clear_old_moneyline_outputs():
    for f in OUTPUT_DIR.glob("*_NBA_moneyline.csv"):
        f.unlink(missing_ok=True)
    for f in OUTPUT_DIR.glob("*_NCAAB_moneyline.csv"):
        f.unlink(missing_ok=True)


# =========================
# CONFIG LOAD
# =========================

NBA_JT = pd.read_csv(NBA_CONFIG)
NCAAB_JT = pd.read_csv(NCAAB_CONFIG)

for col in ["band_min", "band_max", "extra_juice"]:
    if col in NBA_JT.columns:
        NBA_JT[col] = pd.to_numeric(NBA_JT[col], errors="coerce")

for col in ["prob_bin_min", "prob_bin_max", "extra_juice"]:
    if col in NCAAB_JT.columns:
        NCAAB_JT[col] = pd.to_numeric(NCAAB_JT[col], errors="coerce")


# =========================
# NORMALIZATION
# =========================

def normalize_moneyline_inputs(df, file_name=""):

    required = [
        "home_dk_moneyline_american",
        "away_dk_moneyline_american",
        "home_acceptable_decimal_moneyline",
        "away_acceptable_decimal_moneyline",
        "home_acceptable_american_moneyline",
        "away_acceptable_american_moneyline",
        "home_prob",
        "away_prob",
    ]

    validate_columns(df, required, file_name)

    numeric_cols = [
        "home_dk_moneyline_american",
        "away_dk_moneyline_american",
        "home_acceptable_decimal_moneyline",
        "away_acceptable_decimal_moneyline",
        "home_prob",
        "away_prob",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["home_acceptable_american_moneyline", "away_acceptable_american_moneyline"]:
        df[col] = df[col].apply(normalize_american_value)

    return df


# =========================
# NBA JUICE
# =========================

def apply_nba(df):

    df = df.copy()

    # HOME SIDE
    home_merge = NBA_JT[NBA_JT["venue"] == "home"][
        ["band_min", "band_max", "fav_ud", "extra_juice"]
    ].rename(columns={"extra_juice": "home_extra_juice"})

    df["home_fav_ud"] = df["home_dk_moneyline_american"].apply(
        lambda x: "favorite" if pd.notna(x) and x < 0 else "underdog"
    )

    df = df.merge(home_merge, left_on="home_fav_ud", right_on="fav_ud", how="left")

    df["home_band_match"] = df["home_dk_moneyline_american"].between(
        df["band_min"], df["band_max"], inclusive="both"
    )

    df["home_extra_juice"] = df["home_extra_juice"].where(df["home_band_match"])
    df["home_extra_juice"] = df["home_extra_juice"].fillna(0).apply(safe_extra)

    df = (
        df.sort_values(["game_id", "home_band_match"], ascending=[True, False])
        .drop_duplicates(subset=["game_id"], keep="first")
    )

    df = df.drop(columns=["band_min", "band_max", "fav_ud", "home_band_match"], errors="ignore")

    # AWAY SIDE
    away_merge = NBA_JT[NBA_JT["venue"] == "away"][
        ["band_min", "band_max", "fav_ud", "extra_juice"]
    ].rename(columns={"extra_juice": "away_extra_juice"})

    df["away_fav_ud"] = df["away_dk_moneyline_american"].apply(
        lambda x: "favorite" if pd.notna(x) and x < 0 else "underdog"
    )

    df = df.merge(away_merge, left_on="away_fav_ud", right_on="fav_ud", how="left")

    df["away_band_match"] = df["away_dk_moneyline_american"].between(
        df["band_min"], df["band_max"], inclusive="both"
    )

    df["away_extra_juice"] = df["away_extra_juice"].where(df["away_band_match"])
    df["away_extra_juice"] = df["away_extra_juice"].fillna(0).apply(safe_extra)

    df = (
        df.sort_values(["game_id", "away_band_match"], ascending=[True, False])
        .drop_duplicates(subset=["game_id"], keep="first")
    )

    df = df.drop(columns=["band_min", "band_max", "fav_ud", "away_band_match"], errors="ignore")

    # FINAL PRICE
    df["home_juice_decimal_moneyline"] = (
        df["home_acceptable_decimal_moneyline"].apply(safe_decimal) *
        (1 + df["home_extra_juice"])
    )

    df["away_juice_decimal_moneyline"] = (
        df["away_acceptable_decimal_moneyline"].apply(safe_decimal) *
        (1 + df["away_extra_juice"])
    )

    df["home_juice_odds"] = df["home_juice_decimal_moneyline"].apply(decimal_to_american)
    df["away_juice_odds"] = df["away_juice_decimal_moneyline"].apply(decimal_to_american)

    df["home_acceptable_decimal_moneyline"] = df["home_juice_decimal_moneyline"]
    df["away_acceptable_decimal_moneyline"] = df["away_juice_decimal_moneyline"]

    df["home_acceptable_american_moneyline"] = df["home_juice_odds"]
    df["away_acceptable_american_moneyline"] = df["away_juice_odds"]

    return df


# =========================
# NCAAB JUICE
# =========================

def apply_ncaab(df):

    df = df.copy()

    bins = NCAAB_JT

    df["_key"] = 1
    bins["_key"] = 1

    df = df.merge(bins, on="_key", how="left")

    df["home_prob_match"] = (
        (df["home_prob"] >= df["prob_bin_min"]) &
        (df["home_prob"] < df["prob_bin_max"])
    )

    df["away_prob_match"] = (
        (df["away_prob"] >= df["prob_bin_min"]) &
        (df["away_prob"] < df["prob_bin_max"])
    )

    df["home_extra_juice"] = df["extra_juice"].where(df["home_prob_match"]).fillna(0)
    df["away_extra_juice"] = df["extra_juice"].where(df["away_prob_match"]).fillna(0)

    df = (
        df.sort_values(["game_id", "home_prob_match"], ascending=[True, False])
        .drop_duplicates(subset=["game_id"], keep="first")
    )

    base_home = df["home_acceptable_american_moneyline"].apply(american_to_decimal).apply(safe_decimal)
    base_away = df["away_acceptable_american_moneyline"].apply(american_to_decimal).apply(safe_decimal)

    df["home_juice_decimal_moneyline"] = base_home * (1 + df["home_extra_juice"])
    df["away_juice_decimal_moneyline"] = base_away * (1 + df["away_extra_juice"])

    df["home_juice_odds"] = df["home_juice_decimal_moneyline"].apply(decimal_to_american)
    df["away_juice_odds"] = df["away_juice_decimal_moneyline"].apply(decimal_to_american)

    df["home_acceptable_decimal_moneyline"] = df["home_juice_decimal_moneyline"]
    df["away_acceptable_decimal_moneyline"] = df["away_juice_decimal_moneyline"]

    df["home_acceptable_american_moneyline"] = df["home_juice_odds"]
    df["away_acceptable_american_moneyline"] = df["away_juice_odds"]

    return df


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write(f"=== APPLY MONEYLINE JUICE START {datetime.utcnow().isoformat()}Z ===\n")

    try:

        clear_old_moneyline_outputs()

        for f in sorted(INPUT_DIR.iterdir()):

            if not f.is_file():
                continue

            if f.name.endswith("_NBA_moneyline.csv"):

                df = pd.read_csv(f)
                df = normalize_moneyline_inputs(df, f.name)
                df = apply_nba(df)

                atomic_write_csv(df, OUTPUT_DIR / f.name)

                audit(ERROR_LOG, "JUICE_ML_NBA", "SUCCESS", msg=f.name, df=df)

            elif f.name.endswith("_NCAAB_moneyline.csv"):

                df = pd.read_csv(f)
                df = normalize_moneyline_inputs(df, f.name)
                df = apply_ncaab(df)

                atomic_write_csv(df, OUTPUT_DIR / f.name)

                audit(ERROR_LOG, "JUICE_ML_NCAAB", "SUCCESS", msg=f.name, df=df)

    except Exception as e:

        audit(ERROR_LOG, "JUICE_ML_CRITICAL", "FAILED", msg=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
