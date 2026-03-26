#!/usr/bin/env python3

# docs/win/baseball/scripts/02_juice/apply_moneyline_juice.py

import glob
import math
import sys
import traceback
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd

INPUT_DIR = Path("docs/win/baseball/01_merge/01_merguiced")
OUTPUT_DIR = Path("docs/win/baseball/02_juice")
JUICE_FILE = Path("config/baseball/mlb/mlb_ml_juice.csv")

ERROR_DIR = Path("docs/win/baseball/errors/02_juice")
LOG_FILE = ERROR_DIR / "apply_moneyline_juice.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def _now():
    return datetime.now(UTC).isoformat()


def _log(msg: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")


def find_band_row(juice_df, american, fav_ud, venue):
    band = juice_df[
        (juice_df["band_min"] <= american) &
        (american <= juice_df["band_max"]) &
        (juice_df["fav_ud"] == fav_ud) &
        (juice_df["venue"] == venue)
    ]

    if len(band) != 1:
        return None

    return float(band.iloc[0]["extra_juice"])


def process_row(df, juice_df, idx, row, file_path):
    try:
        home_american = float(row["home_dk_moneyline_american"])
        away_american = float(row["away_dk_moneyline_american"])
        home_fair = float(row["home_fair_decimal_moneyline"])
        away_fair = float(row["away_fair_decimal_moneyline"])
    except Exception:
        _log(f"[ROW SKIP] idx={idx} reason=conversion_failed")
        return df

    if not math.isfinite(home_fair) or home_fair <= 1:
        _log(f"[ROW SKIP] idx={idx} reason=invalid_home_fair val={home_fair}")
        return df

    if not math.isfinite(away_fair) or away_fair <= 1:
        _log(f"[ROW SKIP] idx={idx} reason=invalid_away_fair val={away_fair}")
        return df

    home_fav_ud = "favorite" if home_american < 0 else "underdog"
    away_fav_ud = "favorite" if away_american < 0 else "underdog"

    home_extra = find_band_row(juice_df, home_american, home_fav_ud, "home")
    away_extra = find_band_row(juice_df, away_american, away_fav_ud, "away")

    if home_extra is None or away_extra is None:
        _log(
            f"[ROW SKIP] idx={idx} reason=band_lookup_failed "
            f"home={home_american} away={away_american}"
        )
        return df

    home_juiced_decimal = home_fair * (1 - home_extra)
    away_juiced_decimal = away_fair * (1 - away_extra)

    if home_juiced_decimal <= 1 or away_juiced_decimal <= 1:
        _log(
            f"[ROW SKIP] idx={idx} reason=invalid_juiced_decimal "
            f"home={home_juiced_decimal} away={away_juiced_decimal}"
        )
        return df

    home_juiced_prob = 1 / home_juiced_decimal
    away_juiced_prob = 1 / away_juiced_decimal

    total = home_juiced_prob + away_juiced_prob

    if not math.isfinite(total) or total <= 0:
        _log(f"[ROW SKIP] idx={idx} reason=invalid_normalization_total val={total}")
        return df

    home_normalized = home_juiced_prob / total
    away_normalized = away_juiced_prob / total

    df.at[idx, "home_juiced_decimal_moneyline"] = home_juiced_decimal
    df.at[idx, "away_juiced_decimal_moneyline"] = away_juiced_decimal

    df.at[idx, "home_juiced_prob_moneyline"] = home_juiced_prob
    df.at[idx, "away_juiced_prob_moneyline"] = away_juiced_prob

    df.at[idx, "home_normalized_prob_moneyline"] = home_normalized
    df.at[idx, "away_normalized_prob_moneyline"] = away_normalized

    return df


def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== APPLY MONEYLINE JUICE START {_now()} ===\n")

    try:
        _log(f"[INFO] INPUT_DIR: {INPUT_DIR}")
        _log(f"[INFO] JUICE_FILE: {JUICE_FILE}")

        juice_df = pd.read_csv(JUICE_FILE)

        juice_df["band_min"] = pd.to_numeric(juice_df["band_min"], errors="coerce")
        juice_df["band_max"] = pd.to_numeric(juice_df["band_max"], errors="coerce")
        juice_df["extra_juice"] = pd.to_numeric(juice_df["extra_juice"], errors="coerce")
        juice_df["fav_ud"] = juice_df["fav_ud"].astype(str).str.strip()
        juice_df["venue"] = juice_df["venue"].astype(str).str.strip()

        files = sorted(glob.glob(str(INPUT_DIR / "*_mlb_moneyline.csv")))
        _log(f"[INFO] Files found: {len(files)}")

        for file_path in files:
            in_path = Path(file_path)
            out_path = OUTPUT_DIR / in_path.name

            _log(f"\n=== FILE START {_now()} ===")
            _log(f"[INFO] {in_path}")

            df = pd.read_csv(file_path)

            if df.empty:
                _log("[INFO] Empty file — skipping")
                continue

            cols = [
                "home_dk_moneyline_american",
                "away_dk_moneyline_american",
                "home_fair_decimal_moneyline",
                "away_fair_decimal_moneyline",
            ]

            for c in cols:
                df[c] = pd.to_numeric(df[c], errors="coerce")

            df["home_juiced_prob_moneyline"] = pd.NA
            df["away_juiced_prob_moneyline"] = pd.NA
            df["home_juiced_decimal_moneyline"] = pd.NA
            df["away_juiced_decimal_moneyline"] = pd.NA
            df["home_normalized_prob_moneyline"] = pd.NA
            df["away_normalized_prob_moneyline"] = pd.NA

            applied = 0
            skipped = 0

            for idx, row in df.iterrows():
                before = df.at[idx, "home_juiced_decimal_moneyline"]
                df = process_row(df, juice_df, idx, row, file_path)
                after = df.at[idx, "home_juiced_decimal_moneyline"]

                if pd.isna(before) and not pd.isna(after):
                    applied += 1
                elif pd.isna(after):
                    skipped += 1

            _log(f"[SUMMARY] applied={applied} skipped={skipped}")

            df.to_csv(out_path, index=False)
            _log(f"[INFO] Wrote: {out_path}")
            _log(f"=== FILE END {_now()} ===")

        _log(f"\n=== COMPLETE {_now()} ===")

    except Exception as e:
        _log("\n=== ERROR ===")
        _log(str(e))
        _log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
