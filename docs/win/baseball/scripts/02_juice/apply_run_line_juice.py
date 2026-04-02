#!/usr/bin/env python3

# docs/win/baseball/scripts/02_juice/apply_run_line_juice.py

import glob
import math
import sys
import traceback
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd

INPUT_DIR = Path("docs/win/baseball/01_merge/01_merguiced")
OUTPUT_DIR = Path("docs/win/baseball/02_juice")
JUICE_FILE = Path("config/baseball/mlb/mlb_run_line_juice.csv")

ERROR_DIR = Path("docs/win/baseball/errors/02_juice")
LOG_FILE = ERROR_DIR / "apply_run_line_juice.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def _now():
    return datetime.now(UTC).isoformat()


def _log(msg: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")


def find_band_row(juice_df, dk_odds, venue, fav_ud):
    band = juice_df[
        (juice_df["band_min"] <= dk_odds) &
        (juice_df["band_max"] > dk_odds) &
        (juice_df["venue"] == venue) &
        (juice_df["fav_ud"] == fav_ud)
    ]

    if band.empty:
        return None

    if len(band) > 1:
        _log(
            f"[WARN] Multiple band matches dk_odds={dk_odds} "
            f"venue={venue} fav_ud={fav_ud}"
        )

    return float(band.iloc[0]["extra_juice"])


def process_rows(df, juice_df, file_path):
    df["home_juiced_decimal_run_line"] = pd.NA
    df["away_juiced_decimal_run_line"] = pd.NA
    df["home_juiced_prob_run_line"] = pd.NA
    df["away_juiced_prob_run_line"] = pd.NA

    df["home_normalized_prob_run_line"] = pd.NA
    df["away_normalized_prob_run_line"] = pd.NA

    applied = 0
    skipped_no_band = 0
    skipped_bad = 0

    for idx, row in df.iterrows():
        try:
            home_dk_odds = float(row["home_dk_run_line_american"])
            away_dk_odds = float(row["away_dk_run_line_american"])

            # FIX 1: use MARKET decimal odds (not fair)
            home_dec = float(row["home_dk_run_line_decimal"])
            away_dec = float(row["away_dk_run_line_decimal"])

        except Exception:
            skipped_bad += 1
            _log(f"[ROW SKIP] idx={idx} reason=cast_error")
            continue

        if (
            not math.isfinite(home_dec) or home_dec <= 1 or
            not math.isfinite(away_dec) or away_dec <= 1
        ):
            skipped_bad += 1
            _log(f"[ROW SKIP] idx={idx} reason=bad_decimal")
            continue

        home_fav_ud = "favorite" if home_dk_odds < 0 else "underdog"
        away_fav_ud = "favorite" if away_dk_odds < 0 else "underdog"

        home_extra = find_band_row(juice_df, home_dk_odds, "home", home_fav_ud)
        away_extra = find_band_row(juice_df, away_dk_odds, "away", away_fav_ud)

        if home_extra is None or away_extra is None:
            skipped_no_band += 1
            _log(
                f"[ROW SKIP] idx={idx} reason=no_band "
                f"home_dk_odds={home_dk_odds} away_dk_odds={away_dk_odds}"
            )
            continue

        try:
            home_prob = 1 / home_dec
            away_prob = 1 / away_dec

            # FIX 2: correct directional application
            if home_fav_ud == "favorite":
                home_adj = home_prob * (1 - home_extra)
            else:
                home_adj = home_prob * (1 + home_extra)

            if away_fav_ud == "favorite":
                away_adj = away_prob * (1 - away_extra)
            else:
                away_adj = away_prob * (1 + away_extra)

            home_adj = max(home_adj, 1e-6)
            away_adj = max(away_adj, 1e-6)

            total = home_adj + away_adj
            if total <= 0 or not math.isfinite(total):
                skipped_bad += 1
                _log(f"[ROW SKIP] idx={idx} reason=bad_total")
                continue

            home_final = home_adj / total
            away_final = away_adj / total

            home_juiced_decimal = 1 / home_final
            away_juiced_decimal = 1 / away_final

        except Exception:
            skipped_bad += 1
            _log(f"[ROW SKIP] idx={idx} reason=calc_error")
            continue

        df.at[idx, "home_juiced_prob_run_line"] = home_final
        df.at[idx, "away_juiced_prob_run_line"] = away_final

        df.at[idx, "home_juiced_decimal_run_line"] = home_juiced_decimal
        df.at[idx, "away_juiced_decimal_run_line"] = away_juiced_decimal

        df.at[idx, "home_normalized_prob_run_line"] = home_final
        df.at[idx, "away_normalized_prob_run_line"] = away_final

        applied += 1

    return df, applied, skipped_no_band, skipped_bad


def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== APPLY RUN LINE JUICE START {_now()} ===\n")

    try:
        _log(f"[INFO] INPUT_DIR: {INPUT_DIR}")
        _log(f"[INFO] JUICE_FILE: {JUICE_FILE}")

        juice_df = pd.read_csv(JUICE_FILE)

        juice_df["band_min"] = juice_df["band_min"].astype(float)
        juice_df["band_max"] = juice_df["band_max"].astype(float)
        juice_df["venue"] = juice_df["venue"].astype(str).str.strip()
        juice_df["fav_ud"] = juice_df["fav_ud"].astype(str).str.strip()
        juice_df["extra_juice"] = juice_df["extra_juice"].astype(float)

        files = sorted(glob.glob(str(INPUT_DIR / "*_mlb_run_line.csv")))
        _log(f"[INFO] Files found: {len(files)}")

        for file_path in files:
            in_path = Path(file_path)
            out_path = OUTPUT_DIR / in_path.name

            _log(f"\n=== FILE START {_now()} ===")
            _log(f"[INFO] {in_path}")

            df = pd.read_csv(in_path)

            df, applied, no_band, bad = process_rows(df, juice_df, file_path)

            _log(f"[SUMMARY] applied={applied} no_band={no_band} bad={bad}")

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
