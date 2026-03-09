#!/usr/bin/env python3
# docs/win/basketball/scripts/02_juice/apply_spread_juice.py

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

NBA_CONFIG = Path("config/basketball/nba/nba_spreads_juice.csv")
NCAAB_CONFIG = Path("config/basketball/ncaab/ncaab_spreads_juice.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = ERROR_DIR / "apply_spread_juice.txt"

# =========================
# LOAD CONFIG ONCE
# =========================

NBA_JUICE_TABLE = pd.read_csv(NBA_CONFIG)
NCAAB_JUICE_TABLE = pd.read_csv(NCAAB_CONFIG)

# =========================
# CLEAN OLD FILES
# =========================

for f in OUTPUT_DIR.glob("*_NBA_spread.csv"):
    f.unlink(missing_ok=True)

for f in OUTPUT_DIR.glob("*_NCAAB_spread.csv"):
    f.unlink(missing_ok=True)

# =========================
# LOG
# =========================

def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# HELPERS
# =========================

def validate_columns(df, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

def normalize_american(val):
    if pd.isna(val):
        return None
    text = str(val).replace("+","").strip()
    try:
        return float(text)
    except:
        return None

def american_to_decimal(a):
    a = normalize_american(a)
    if a is None:
        return None
    return 1 + (a/100 if a>0 else 100/abs(a))

def decimal_to_american(d):
    try:
        d=float(d)
    except:
        return ""

    if not math.isfinite(d) or d<=1:
        return ""

    if d>=2:
        return f"+{int(round((d-1)*100))}"
    return f"-{int(round(100/(d-1)))}"

def safe_decimal(v):
    try:
        v=float(v)
    except:
        return 1.01

    if not math.isfinite(v) or v<=1:
        return 1.01

    return v

def atomic_write(df,path):
    tmp=path.with_suffix(".tmp")
    df.to_csv(tmp,index=False)
    tmp.replace(path)

# =========================
# ENSURE AMERICAN COLS
# =========================

def ensure_american_columns(df):
    for side in ["home","away"]:
        amer=f"{side}_acceptable_spread_american"
        dec=f"{side}_acceptable_spread_decimal"

        if amer not in df.columns and dec in df.columns:
            df[amer]=df[dec].apply(decimal_to_american)

    return df

# =========================
# NBA SPREAD JUICE
# =========================

def apply_nba(df):

    df=ensure_american_columns(df)

    required=[
        "home_spread","away_spread",
        "home_acceptable_spread_american",
        "away_acceptable_spread_american"
    ]

    validate_columns(df,required)

    jt=NBA_JUICE_TABLE

    def process(row,side):

        spread=float(row[f"{side}_spread"])
        odds=row[f"{side}_acceptable_spread_american"]

        odds=normalize_american(odds)

        fav_ud="favorite" if spread<0 else "underdog"

        band=jt[
            (jt.band_min<=abs(spread))&
            (abs(spread)<=jt.band_max)&
            (jt.fav_ud==fav_ud)&
            (jt.venue==side)
        ]

        extra=band.iloc[0]["extra_juice"] if not band.empty else 0.0

        if not math.isfinite(extra):
            extra=0.0

        base=american_to_decimal(odds)
        base=safe_decimal(base)

        final=base*(1+extra)

        return final,decimal_to_american(final)

    for side in ["home","away"]:

        df[[f"{side}_spread_juice_decimal",
            f"{side}_spread_juice_odds"]]=df.apply(
            lambda r:process(r,side),
            axis=1,
            result_type="expand"
        )

    # replace acceptable prices so edges use juice-adjusted
    df["home_acceptable_spread_decimal"]=df["home_spread_juice_decimal"]
    df["away_acceptable_spread_decimal"]=df["away_spread_juice_decimal"]

    df["home_acceptable_spread_american"]=df["home_spread_juice_odds"]
    df["away_acceptable_spread_american"]=df["away_spread_juice_odds"]

    return df

# =========================
# NCAAB SPREAD JUICE
# =========================

def apply_ncaab(df):

    df=ensure_american_columns(df)

    required=[
        "home_spread","away_spread",
        "home_acceptable_spread_american",
        "away_acceptable_spread_american"
    ]

    validate_columns(df,required)

    jt=NCAAB_JUICE_TABLE

    def process(row,side):

        spread=float(row[f"{side}_spread"])
        odds=row[f"{side}_acceptable_spread_american"]

        odds=normalize_american(odds)

        match=jt[jt.spread==spread]

        extra=match.iloc[0]["extra_juice"] if not match.empty else 0.0

        if not math.isfinite(extra):
            extra=0.0

        base=american_to_decimal(odds)
        base=safe_decimal(base)

        final=base*(1+extra)

        return final,decimal_to_american(final)

    for side in ["home","away"]:

        df[[f"{side}_spread_juice_decimal",
            f"{side}_spread_juice_odds"]]=df.apply(
            lambda r:process(r,side),
            axis=1,
            result_type="expand"
        )

    df["home_acceptable_spread_decimal"]=df["home_spread_juice_decimal"]
    df["away_acceptable_spread_decimal"]=df["away_spread_juice_decimal"]

    df["home_acceptable_spread_american"]=df["home_spread_juice_odds"]
    df["away_acceptable_spread_american"]=df["away_spread_juice_odds"]

    return df

# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG,"w") as f:
        f.write(f"=== APPLY SPREAD JUICE START {datetime.utcnow().isoformat()}Z ===\n")

    try:

        files=0

        for f in INPUT_DIR.iterdir():

            name=f.name

            if name.endswith("_NBA_spread.csv"):

                df=pd.read_csv(f)

                df=apply_nba(df)

                atomic_write(df,OUTPUT_DIR/name)

                log(f"Processed NBA file: {name}")

                audit(ERROR_LOG,"JUICE_SPREAD_NBA","SUCCESS",
                      msg=f"Applied NBA Spread Juice to {name}",
                      df=df)

                files+=1

            elif name.endswith("_NCAAB_spread.csv"):

                df=pd.read_csv(f)

                df=apply_ncaab(df)

                atomic_write(df,OUTPUT_DIR/name)

                log(f"Processed NCAAB file: {name}")

                audit(ERROR_LOG,"JUICE_SPREAD_NCAAB","SUCCESS",
                      msg=f"Applied NCAAB Spread Juice to {name}",
                      df=df)

                files+=1

        log(f"Total files processed: {files}")
        log("=== APPLY SPREAD JUICE END ===")

    except Exception as e:

        log("=== ERROR ===")
        log(str(e))
        log(traceback.format_exc())

        audit(ERROR_LOG,"JUICE_SPREAD_CRITICAL","FAILED",msg=str(e))

        sys.exit(1)

if __name__=="__main__":
    main()
