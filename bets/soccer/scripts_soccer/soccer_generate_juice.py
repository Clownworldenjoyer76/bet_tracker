#!/usr/bin/env python3
"""
scripts/soccer_generate_juice.py

Builds a production-grade Bundesliga 1X2 juice config
from the master calibration output.

Input:
  bets/soccer/calibration/soccer_calibration_master.csv

Output:
  config/soccer/bundesliga_1x2_juice.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# PATHS
# =========================

MASTER_FILE = Path("bets/soccer/calibration/soccer_calibration_master.csv")
OUTPUT_DIR = Path("config/soccer")
OUTPUT_FILE = OUTPUT_DIR / "bundesliga_1x2_juice.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONFIG
# =========================

LEAGUE_FILTER = "BUNDESLIGA"
BASE_BUCKET_WIDTH = 0.05
MIN_SAMPLE = 250
MAX_ABS_JUICE = 0.05
ENFORCE_NONINCREASING = True

# =========================
# ISOTONIC HELPERS
# =========================

def _pav_isotonic_increasing(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    y = y.astype(float)
    w = w.astype(float)

    blocks = [{"sum_w": w[i], "sum_wy": w[i] * y[i], "start": i, "end": i} for i in range(len(y))]

    def block_value(b):
        return b["sum_wy"] / b["sum_w"] if b["sum_w"] > 0 else 0.0

    i = 0
    while i < len(blocks) - 1:
        if block_value(blocks[i]) <= block_value(blocks[i + 1]) + 1e-15:
            i += 1
            continue

        merged = {
            "sum_w": blocks[i]["sum_w"] + blocks[i + 1]["sum_w"],
            "sum_wy": blocks[i]["sum_wy"] + blocks[i + 1]["sum_wy"],
            "start": blocks[i]["start"],
            "end": blocks[i + 1]["end"],
        }
        blocks[i:i + 2] = [merged]
        i = max(i - 1, 0)

    y_hat = np.zeros_like(y, dtype=float)
    for b in blocks:
        val = block_value(b)
        y_hat[b["start"]: b["end"] + 1] = val

    return y_hat


def isotonic_fit(x: np.ndarray, y: np.ndarray, w: np.ndarray, increasing: bool) -> np.ndarray:
    if len(y) == 0:
        return y
    if increasing:
        return _pav_isotonic_increasing(y, w)
    return -_pav_isotonic_increasing(-y, w)

# =========================
# BINNING + TAIL COLLAPSE
# =========================

def make_base_bins(df: pd.DataFrame, width: float) -> pd.DataFrame:
    p = df["implied_prob_fair"].astype(float)
    band_min = np.floor(p / width) * width
    band_min = np.clip(band_min, 0.0, 1.0 - width)
    band_min = np.round(band_min, 4)
    band_max = np.round(band_min + width, 4)

    tmp = df.copy()
    tmp["band_min"] = band_min
    tmp["band_max"] = band_max

    g = tmp.groupby(["band_min", "band_max"], as_index=False).agg(
        n=("result", "count"),
        avg_prob=("implied_prob_fair", "mean"),
        actual_win_rate=("result", "mean"),
    )

    g["delta"] = g["avg_prob"] - g["actual_win_rate"]
    return g.sort_values(["band_min", "band_max"]).reset_index(drop=True)


def collapse_sparse_tails(bins_df: pd.DataFrame, min_n: int) -> pd.DataFrame:
    if bins_df.empty:
        return bins_df

    bins = bins_df.copy().reset_index(drop=True)

    def merge_rows(a, b):
        n1, n2 = float(a["n"]), float(b["n"])
        nt = n1 + n2

        avg_prob = (a["avg_prob"] * n1 + b["avg_prob"] * n2) / nt
        actual = (a["actual_win_rate"] * n1 + b["actual_win_rate"] * n2) / nt

        out = a.copy()
        out["band_min"] = min(float(a["band_min"]), float(b["band_min"]))
        out["band_max"] = max(float(a["band_max"]), float(b["band_max"]))
        out["n"] = int(nt)
        out["avg_prob"] = avg_prob
        out["actual_win_rate"] = actual
        out["delta"] = avg_prob - actual
        return out

    while len(bins) >= 2 and int(bins.loc[0, "n"]) < min_n:
        merged = merge_rows(bins.loc[0], bins.loc[1])
        bins = pd.concat([pd.DataFrame([merged]), bins.iloc[2:]], ignore_index=True)

    while len(bins) >= 2 and int(bins.loc[len(bins)-1, "n"]) < min_n:
        merged = merge_rows(bins.loc[len(bins)-2], bins.loc[len(bins)-1])
        bins = pd.concat([bins.iloc[:-2], pd.DataFrame([merged])], ignore_index=True)

    return bins.reset_index(drop=True)

# =========================
# BUILD CURVE PER SIDE
# =========================

def build_side_curve(df_master: pd.DataFrame, market: str) -> pd.DataFrame:
    sub = df_master[df_master["market"] == market].copy()
    if sub.empty:
        return pd.DataFrame()

    bins = make_base_bins(sub, BASE_BUCKET_WIDTH)
    bins = collapse_sparse_tails(bins, MIN_SAMPLE)
    bins = bins.sort_values("avg_prob").reset_index(drop=True)

    x = bins["avg_prob"].to_numpy()
    y = bins["delta"].to_numpy()
    w = bins["n"].to_numpy()

    y_hat = isotonic_fit(x, y, w, increasing=not ENFORCE_NONINCREASING)
    y_hat = np.clip(y_hat, -MAX_ABS_JUICE, MAX_ABS_JUICE)

    bins["extra_juice"] = y_hat
    return bins.sort_values(["band_min", "band_max"]).reset_index(drop=True)

# =========================
# MAIN
# =========================

def main():
    if not MASTER_FILE.exists():
        print("Calibration master file not found.")
        return

    df = pd.read_csv(MASTER_FILE)
    df = df[df["league"] == LEAGUE_FILTER].copy()
    df = df[(df["implied_prob_fair"] > 0) & (df["implied_prob_fair"] < 1)]

    if df.empty:
        print("No rows after filtering.")
        return

    juice_rows = []

    for market in ["1x2_home", "1x2_draw", "1x2_away"]:
        curve = build_side_curve(df, market)
        side = market.replace("1x2_", "")

        for _, r in curve.iterrows():
            band_min = float(r["band_min"])
            band_max = float(r["band_max"])

            juice_rows.append({
                "band": f"{band_min:.2f} to {band_max:.2f}",
                "band_min": band_min,
                "band_max": band_max,
                "side": side,
                "extra_juice": float(r["extra_juice"]),
            })

    out = pd.DataFrame(juice_rows)

    side_order = {"home": 0, "draw": 1, "away": 2}
    out["side_sort"] = out["side"].map(side_order)
    out = out.sort_values(["side_sort", "band_min"]).drop(columns="side_sort")

    out.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {OUTPUT_FILE} ({len(out)} rows)")


if __name__ == "__main__":
    main()
