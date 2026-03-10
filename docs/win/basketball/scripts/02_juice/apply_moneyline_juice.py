#!/usr/bin/env python3
# docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py

import pandas as pd
from pathlib import Path
import math
from datetime import datetime
import traceback
import sys

# =========================
# LOGGER
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

NBA_CONFIG = Path("config/basketball/nba/nba_ml_juice.csv")
NCAAB_CONFIG = Path("config/basketball/ncaab/ncaab_ml_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "apply_moneyline_juice.txt"


# =========================
# SIMPLE LOG
# =========================

def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


# =========================
# HELPERS
# =========================

def normalize_american_value(val):

    if pd.isna(val):
        return None

    text = str(val).strip().replace(",", "")

    if text == "":
        return None

    try:
        return float(text)
    except:
        return None


def american_to_decimal(a):

    a = normalize_american_value(a)

    if a is None or a == 0:
        return None

    return 1 + (a/100 if a > 0 else 100/abs(a))


def decimal_to_american(d):

    try:
        d = float(d)
    except:
        return ""

    if not math.isfinite(d) or d <= 1:
        return ""

    if d >= 2:
        return f"+{int(round((d-1)*100))}"

    return f"-{int(round(100/(d-1)))}"


def safe_decimal(v):

    try:
        v = float(v)
    except:
        return 1.01

    if not math.isfinite(v) or v <= 1:
        return 1.01

    return v


def atomic_write(df, path):

    tmp = path.with_suffix(".tmp")

    df.to_csv(tmp, index=False)

    tmp.replace(path)


def clear_old_moneyline_outputs():

    for f in OUTPUT_DIR.glob("*_NBA_moneyline.csv"):
        f.unlink(missing_ok=True)

    for f in OUTPUT_DIR.glob("*_NCAAB_moneyline.csv"):
        f.unlink(missing_ok=True)


# =========================
# LOAD CONFIG
# =========================

NBA_JT = pd.read_csv(NBA_CONFIG)
NCAAB_JT = pd.read_csv(NCAAB_CONFIG)


# =========================
# NBA JUICE
# =========================

def lookup_nba_extra(price, venue):

    if pd.isna(price):
        return 0.0

    fav_ud = "favorite" if price < 0 else "underdog"

    rows = NBA_JT[
        (NBA_JT["venue"] == venue)
        & (NBA_JT["fav_ud"] == fav_ud)
        & (price >= NBA_JT["band_min"])
        & (price <= NBA_JT["band_max"])
    ]

    if rows.empty:
        return 0.0

    return float(rows.iloc[0]["extra_juice"])


def apply_nba(df):

    df = df.copy()

    df["home_extra_juice"] = df["home_dk_moneyline_american"].apply(
        lambda x: lookup_nba_extra(x, "home")
    )

    df["away_extra_juice"] = df["away_dk_moneyline_american"].apply(
        lambda x: lookup_nba_extra(x, "away")
    )

    df["home_juice_decimal_moneyline"] = (
        pd.to_numeric(df["home_acceptable_decimal_moneyline"], errors="coerce").apply(safe_decimal)
        * (1 + df["home_extra_juice"])
    )

    df["away_juice_decimal_moneyline"] = (
        pd.to_numeric(df["away_acceptable_decimal_moneyline"], errors="coerce").apply(safe_decimal)
        * (1 + df["away_extra_juice"])
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

def lookup_ncaab_extra(prob):

    if pd.isna(prob):
        return 0.0

    rows = NCAAB_JT[
        (prob >= NCAAB_JT["prob_bin_min"])
        & (prob < NCAAB_JT["prob_bin_max"])
    ]

    if rows.empty:
        return 0.0

    return float(rows.iloc[0]["extra_juice"])


def apply_ncaab(df):

    df = df.copy()

    df["home_extra_juice"] = df["home_prob"].apply(lookup_ncaab_extra)
    df["away_extra_juice"] = df["away_prob"].apply(lookup_ncaab_extra)

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

    with open(ERROR_LOG, "w") as f:
        f.write(f"=== APPLY MONEYLINE JUICE START {datetime.utcnow().isoformat()}Z ===\n")

    try:

        clear_old_moneyline_outputs()

        files = 0

        for f in INPUT_DIR.iterdir():

            name = f.name

            if name.endswith("_NBA_moneyline.csv"):

                df = pd.read_csv(f)

                df = apply_nba(df)

                atomic_write(df, OUTPUT_DIR/name)

                log(f"Processed NBA file: {name}")

                audit(ERROR_LOG, "JUICE_ML_NBA", "SUCCESS",
                      msg=f"Applied NBA Moneyline Juice to {name}",
                      df=df)

                files += 1


            elif name.endswith("_NCAAB_moneyline.csv"):

                df = pd.read_csv(f)

                df = apply_ncaab(df)

                atomic_write(df, OUTPUT_DIR/name)

                log(f"Processed NCAAB file: {name}")

                audit(ERROR_LOG, "JUICE_ML_NCAAB", "SUCCESS",
                      msg=f"Applied NCAAB Moneyline Juice to {name}",
                      df=df)

                files += 1


        log(f"Total files processed: {files}")
        log("=== APPLY MONEYLINE JUICE END ===")


    except Exception as e:

        log("=== ERROR ===")
        log(str(e))
        log(traceback.format_exc())

        audit(ERROR_LOG, "JUICE_ML_CRITICAL", "FAILED", msg=str(e))

        sys.exit(1)


if __name__ == "__main__":
    main()
