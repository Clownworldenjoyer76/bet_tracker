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

    if df is not None and isinstance(df, pd.DataFrame):
        summary_path = log_path.parent / "condensed_summary.txt"

        play_cols = [c for c in ["home_play", "away_play", "over_play", "under_play"] if c in df.columns]

        if play_cols:
            signals = df[df[play_cols].any(axis=1)].copy()

            if not signals.empty:
                with open(summary_path, "a", encoding="utf-8") as f:
                    f.write(f"\n--- BETTING SIGNALS: {ts} ---\n")

                    base_cols = ["game_date", "home_team", "away_team"]
                    edge_cols = [c for c in df.columns if "edge_pct" in c]

                    final_cols = [c for c in base_cols + edge_cols if c in signals.columns]

                    f.write(signals[final_cols].to_string(index=False))
                    f.write("\n" + "=" * 30 + "\n")


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
# LOGGER
# =========================

def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


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
    removed = 0
    for f in OUTPUT_DIR.glob("*_NBA_moneyline.csv"):
        f.unlink(missing_ok=True)
        removed += 1
    for f in OUTPUT_DIR.glob("*_NCAAB_moneyline.csv"):
        f.unlink(missing_ok=True)
        removed += 1
    log(f"Cleared old moneyline outputs: removed={removed}")


def add_moneyline_juice_diagnostics(df, stage_name):
    diagnostic_cols = [
        "home_extra_juice",
        "away_extra_juice",
        "home_juice_decimal_moneyline",
        "away_juice_decimal_moneyline",
    ]
    existing = [c for c in diagnostic_cols if c in df.columns]
    if not existing or df.empty:
        return

    pieces = []
    for col in existing:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if not series.empty:
            pieces.append(
                f"{col}: avg={series.mean():.6f}, min={series.min():.6f}, max={series.max():.6f}"
            )

    if pieces:
        log(f"{stage_name} diagnostics | " + " | ".join(pieces))


# =========================
# CONFIG LOAD (ONCE)
# =========================

NBA_JT = pd.read_csv(NBA_CONFIG)
NCAAB_JT = pd.read_csv(NCAAB_CONFIG)

# normalize config numeric columns
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

    # venue = home
    home_mask = NBA_JT["venue"].eq("home")
    home_merge = NBA_JT.loc[home_mask, ["band_min", "band_max", "fav_ud", "extra_juice"]].copy()
    home_merge = home_merge.rename(columns={"extra_juice": "home_extra_juice"})

    df["home_fav_ud"] = df["home_dk_moneyline_american"].apply(
        lambda x: "favorite" if pd.notna(x) and x < 0 else "underdog"
    )

    df = df.merge(home_merge, left_on="home_fav_ud", right_on="fav_ud", how="left")
    df["home_band_match"] = (
        pd.to_numeric(df["home_dk_moneyline_american"], errors="coerce").between(df["band_min"], df["band_max"], inclusive="both")
    )
    df["home_extra_juice"] = df["home_extra_juice"].where(df["home_band_match"])
    df["home_extra_juice"] = pd.to_numeric(df["home_extra_juice"], errors="coerce").fillna(0.0)
    df["home_extra_juice"] = df["home_extra_juice"].apply(safe_extra)
    df = df.drop(columns=["band_min", "band_max", "fav_ud", "home_band_match"], errors="ignore")

    # venue = away
    away_mask = NBA_JT["venue"].eq("away")
    away_merge = NBA_JT.loc[away_mask, ["band_min", "band_max", "fav_ud", "extra_juice"]].copy()
    away_merge = away_merge.rename(columns={"extra_juice": "away_extra_juice"})

    df["away_fav_ud"] = df["away_dk_moneyline_american"].apply(
        lambda x: "favorite" if pd.notna(x) and x < 0 else "underdog"
    )

    df = df.merge(away_merge, left_on="away_fav_ud", right_on="fav_ud", how="left")
    df["away_band_match"] = (
        pd.to_numeric(df["away_dk_moneyline_american"], errors="coerce").between(df["band_min"], df["band_max"], inclusive="both")
    )
    df["away_extra_juice"] = df["away_extra_juice"].where(df["away_band_match"])
    df["away_extra_juice"] = pd.to_numeric(df["away_extra_juice"], errors="coerce").fillna(0.0)
    df["away_extra_juice"] = df["away_extra_juice"].apply(safe_extra)
    df = df.drop(columns=["band_min", "band_max", "fav_ud", "away_band_match"], errors="ignore")

    df["home_juice_decimal_moneyline"] = (
        pd.to_numeric(df["home_acceptable_decimal_moneyline"], errors="coerce").apply(safe_decimal)
        * (1 + df["home_extra_juice"])
    )
    df["away_juice_decimal_moneyline"] = (
        pd.to_numeric(df["away_acceptable_decimal_moneyline"], errors="coerce").apply(safe_decimal)
        * (1 + df["away_extra_juice"])
    )

    df["home_juice_decimal_moneyline"] = df["home_juice_decimal_moneyline"].apply(safe_decimal)
    df["away_juice_decimal_moneyline"] = df["away_juice_decimal_moneyline"].apply(safe_decimal)

    df["home_juice_odds"] = df["home_juice_decimal_moneyline"].apply(decimal_to_american)
    df["away_juice_odds"] = df["away_juice_decimal_moneyline"].apply(decimal_to_american)

    # Make downstream stages consume juice-adjusted prices
    df["home_acceptable_decimal_moneyline"] = df["home_juice_decimal_moneyline"]
    df["away_acceptable_decimal_moneyline"] = df["away_juice_decimal_moneyline"]
    df["home_acceptable_american_moneyline"] = df["home_juice_odds"]
    df["away_acceptable_american_moneyline"] = df["away_juice_odds"]

    df = df.drop(columns=["home_fav_ud", "away_fav_ud"], errors="ignore")

    return df


# =========================
# NCAAB JUICE
# =========================

def apply_ncaab(df):
    df = df.copy()

    home_bins = NCAAB_JT.rename(columns={"extra_juice": "home_extra_juice"})
    away_bins = NCAAB_JT.rename(columns={"extra_juice": "away_extra_juice"})

    # home side
    df["_home_key"] = 1
    home_bins["_home_key"] = 1
    df = df.merge(home_bins, on="_home_key", how="left")
    df["home_prob_match"] = (
        (pd.to_numeric(df["home_prob"], errors="coerce") >= df["prob_bin_min"]) &
        (pd.to_numeric(df["home_prob"], errors="coerce") < df["prob_bin_max"])
    )
    df["home_extra_juice"] = df["home_extra_juice"].where(df["home_prob_match"])
    df["home_extra_juice"] = pd.to_numeric(df["home_extra_juice"], errors="coerce").fillna(0.0)
    df["home_extra_juice"] = df["home_extra_juice"].apply(safe_extra)
    df = (
        df.sort_values(["game_id", "home_prob_match"], ascending=[True, False], kind="mergesort")
          .drop_duplicates(subset=["game_id"], keep="first")
    )
    df = df.drop(columns=["prob_bin_min", "prob_bin_max", "_home_key", "home_prob_match"], errors="ignore")

    # away side
    df["_away_key"] = 1
    away_bins["_away_key"] = 1
    df = df.merge(away_bins, on="_away_key", how="left")
    df["away_prob_match"] = (
        (pd.to_numeric(df["away_prob"], errors="coerce") >= df["prob_bin_min"]) &
        (pd.to_numeric(df["away_prob"], errors="coerce") < df["prob_bin_max"])
    )
    df["away_extra_juice"] = df["away_extra_juice"].where(df["away_prob_match"])
    df["away_extra_juice"] = pd.to_numeric(df["away_extra_juice"], errors="coerce").fillna(0.0)
    df["away_extra_juice"] = df["away_extra_juice"].apply(safe_extra)
    df = (
        df.sort_values(["game_id", "away_prob_match"], ascending=[True, False], kind="mergesort")
          .drop_duplicates(subset=["game_id"], keep="first")
    )
    df = df.drop(columns=["prob_bin_min", "prob_bin_max", "_away_key", "away_prob_match"], errors="ignore")

    base_home_decimal = df["home_acceptable_american_moneyline"].apply(american_to_decimal).apply(safe_decimal)
    base_away_decimal = df["away_acceptable_american_moneyline"].apply(american_to_decimal).apply(safe_decimal)

    df["home_juice_decimal_moneyline"] = base_home_decimal * (1 + df["home_extra_juice"])
    df["away_juice_decimal_moneyline"] = base_away_decimal * (1 + df["away_extra_juice"])

    df["home_juice_decimal_moneyline"] = df["home_juice_decimal_moneyline"].apply(safe_decimal)
    df["away_juice_decimal_moneyline"] = df["away_juice_decimal_moneyline"].apply(safe_decimal)

    df["home_juice_odds"] = df["home_juice_decimal_moneyline"].apply(decimal_to_american)
    df["away_juice_odds"] = df["away_juice_decimal_moneyline"].apply(decimal_to_american)

    # Make downstream stages consume juice-adjusted prices
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

        files_found = 0

        for f in sorted(INPUT_DIR.iterdir()):
            name = f.name

            if not f.is_file():
                continue

            if name.endswith("_NBA_moneyline.csv"):
                df = pd.read_csv(f)
                df = normalize_moneyline_inputs(df, name)
                df = apply_nba(df)

                output_path = OUTPUT_DIR / name
                atomic_write_csv(df, output_path)

                add_moneyline_juice_diagnostics(df, f"NBA {name}")
                log(f"Processed NBA file: {name}")
                audit(
                    ERROR_LOG,
                    "JUICE_ML_NBA",
                    "SUCCESS",
                    msg=f"Applied NBA Juice to {name}",
                    df=df
                )

                files_found += 1

            elif name.endswith("_NCAAB_moneyline.csv"):
                df = pd.read_csv(f)
                df = normalize_moneyline_inputs(df, name)
                df = apply_ncaab(df)

                output_path = OUTPUT_DIR / name
                atomic_write_csv(df, output_path)

                add_moneyline_juice_diagnostics(df, f"NCAAB {name}")
                log(f"Processed NCAAB file: {name}")
                audit(
                    ERROR_LOG,
                    "JUICE_ML_NCAAB",
                    "SUCCESS",
                    msg=f"Applied NCAAB Juice to {name}",
                    df=df
                )

                files_found += 1

        log(f"Total files processed: {files_found}")
        log("=== APPLY MONEYLINE JUICE END ===")

    except Exception as e:
        log("=== ERROR ===")
        log(str(e))
        log(traceback.format_exc())

        audit(ERROR_LOG, "JUICE_ML_CRITICAL", "FAILED", msg=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
