#!/usr/bin/env python3

# docs/win/baseball/scripts/02_juice/apply_total_juice.py

import glob
import math
import sys
import traceback
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd

INPUT_DIR = Path("docs/win/baseball/01_merge/01_merguiced")
OUTPUT_DIR = Path("docs/win/baseball/02_juice")
JUICE_FILE = Path("config/baseball/mlb/mlb_totals_juice.csv")

ERROR_DIR = Path("docs/win/baseball/errors/02_juice")
LOG_FILE = ERROR_DIR / "apply_total_juice.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def _now():
    return datetime.now(UTC).isoformat()


def _log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")


def find_band_row(juice_df, total, side):
    band = juice_df[
        (juice_df["band_min"] <= total) &
        (total <= juice_df["band_max"]) &
        (juice_df["side"] == side)
    ]

    if band.empty:
        return None

    return float(band.iloc[0]["extra_juice"])


def process_side(df, juice_df, side):
    fair_col = f"fair_total_{side}_decimal"

    juiced_decimal_col = f"{side}_juiced_decimal_total"
    juiced_prob_col = f"{side}_juiced_prob_total"

    df[juiced_decimal_col] = pd.NA
    df[juiced_prob_col] = pd.NA

    applied = 0
    skipped_no_band = 0
    skipped_bad_row = 0

    for idx, row in df.iterrows():
        try:
            total = round(float(row["total"]), 1)
            fair_decimal = float(row[fair_col])
        except Exception:
            skipped_bad_row += 1
            _log(f"[ROW SKIP] idx={idx} side={side} reason=bad_parse")
            continue

        if not math.isfinite(fair_decimal) or fair_decimal <= 1:
            skipped_bad_row += 1
            _log(
                f"[ROW SKIP] idx={idx} side={side} "
                f"reason=bad_fair_decimal val={fair_decimal}"
            )
            continue

        extra = find_band_row(juice_df, total, side)

        if extra is None:
            skipped_no_band += 1
            _log(f"[ROW SKIP] idx={idx} side={side} reason=no_band total={total}")
            continue

        try:
            juiced_decimal = fair_decimal * (1 - extra)

            if not math.isfinite(juiced_decimal) or juiced_decimal <= 1:
                _log(
                    f"[ROW SKIP] idx={idx} side={side} "
                    f"reason=invalid_juiced_decimal val={juiced_decimal} "
                    f"fair={fair_decimal} extra={extra}"
                )
                skipped_bad_row += 1
                continue

            juiced_prob = 1 / juiced_decimal

        except Exception:
            skipped_bad_row += 1
            _log(f"[ROW SKIP] idx={idx} side={side} reason=calc_error")
            continue

        df.at[idx, juiced_decimal_col] = juiced_decimal
        df.at[idx, juiced_prob_col] = juiced_prob
        applied += 1

    return df, applied, skipped_no_band, skipped_bad_row


def apply_normalization(df):
    df["over_normalized_prob_total"] = pd.NA
    df["under_normalized_prob_total"] = pd.NA

    for idx, row in df.iterrows():
        try:
            op = float(row["over_juiced_prob_total"])
            up = float(row["under_juiced_prob_total"])

            if not math.isfinite(op) or not math.isfinite(up):
                continue

            total = op + up
            if total <= 0:
                continue

            df.at[idx, "over_normalized_prob_total"] = op / total
            df.at[idx, "under_normalized_prob_total"] = up / total

        except Exception:
            continue

    return df


def main():
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write(f"=== APPLY TOTAL JUICE START {_now()} ===\n")

    try:
        juice_df = pd.read_csv(JUICE_FILE)

        juice_df["band_min"] = juice_df["band_min"].astype(float)
        juice_df["band_max"] = juice_df["band_max"].astype(float)
        juice_df["side"] = juice_df["side"].astype(str).str.strip()
        juice_df["extra_juice"] = juice_df["extra_juice"].astype(float)

        files = sorted(glob.glob(str(INPUT_DIR / "*_mlb_total.csv")))
        _log(f"[INFO] Files found: {len(files)}")

        if not files:
            raise ValueError("No total files found")

        for file_path in files:
            in_path = Path(file_path)
            out_path = OUTPUT_DIR / in_path.name

            _log(f"\n=== FILE START {_now()} ===")
            _log(f"[INFO] Input: {in_path}")

            df = pd.read_csv(in_path)

            df, o_applied, o_no_band, o_bad = process_side(df, juice_df, "over")
            df, u_applied, u_no_band, u_bad = process_side(df, juice_df, "under")

            df = apply_normalization(df)

            _log(f"[SUMMARY] over applied={o_applied} no_band={o_no_band} bad={o_bad}")
            _log(f"[SUMMARY] under applied={u_applied} no_band={u_no_band} bad={u_bad}")

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
