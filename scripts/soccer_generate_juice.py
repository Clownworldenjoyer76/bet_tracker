#!/usr/bin/env python3
"""
scripts/soccer_generate_juice.py

Builds a production-grade EPL 1X2 juice config from the most recent master calibration output.

Input:
  bets/soccer/calibration/soccer_calibration_master.csv

Output:
  config/soccer/epl_1x2_juice.csv

Key upgrades vs. the prior version:
  - Enforce monotonic smoothing (weighted isotonic regression via PAV)
  - Collapse sparse tails (merge low/high probability bins until MIN_SAMPLE is met)
  - Produce stable bands (less oscillation; optional cap on extreme juice)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# PATHS
# =========================

MASTER_FILE = Path("bets/soccer/calibration/soccer_calibration_master.csv")
OUTPUT_DIR = Path("config/soccer")
OUTPUT_FILE = OUTPUT_DIR / "epl_1x2_juice.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONFIG
# =========================

LEAGUE_FILTER = "EPL"

# Start with fine bins, then collapse only the sparse tails.
BASE_BUCKET_WIDTH = 0.05

# Minimum observations per bin AFTER tail-collapsing
MIN_SAMPLE = 250

# Cap extreme juice to avoid pathological bands (probability shift cap)
MAX_ABS_JUICE = 0.05

# If True, enforce delta(p) to be non-increasing with p (typical favorite-longshot bias shape)
# delta = avg_prob - actual_win_rate
# longshots -> delta positive; favorites -> delta tends to shrink and can go negative
ENFORCE_NONINCREASING = True

# =========================
# ISOTONIC (PAV) HELPERS
# =========================

def _pav_isotonic_increasing(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """
    Weighted Pool-Adjacent-Violators algorithm for isotonic regression with
    increasing constraint: y_hat[0] <= y_hat[1] <= ... <= y_hat[n-1]

    Returns fitted y_hat.
    """
    y = y.astype(float)
    w = w.astype(float)

    # Each point is a block initially
    blocks = [{"sum_w": w[i], "sum_wy": w[i] * y[i], "start": i, "end": i} for i in range(len(y))]

    def block_value(b):
        return b["sum_wy"] / b["sum_w"] if b["sum_w"] > 0 else 0.0

    i = 0
    while i < len(blocks) - 1:
        if block_value(blocks[i]) <= block_value(blocks[i + 1]) + 1e-15:
            i += 1
            continue

        # Merge violating adjacent blocks
        merged = {
            "sum_w": blocks[i]["sum_w"] + blocks[i + 1]["sum_w"],
            "sum_wy": blocks[i]["sum_wy"] + blocks[i + 1]["sum_wy"],
            "start": blocks[i]["start"],
            "end": blocks[i + 1]["end"],
        }
        blocks[i:i + 2] = [merged]

        # Move back to ensure global feasibility
        i = max(i - 1, 0)

    # Expand blocks into fitted y_hat
    y_hat = np.zeros_like(y, dtype=float)
    for b in blocks:
        val = block_value(b)
        y_hat[b["start"] : b["end"] + 1] = val

    return y_hat


def isotonic_fit(x: np.ndarray, y: np.ndarray, w: np.ndarray, increasing: bool) -> np.ndarray:
    """
    Weighted isotonic fit preserving order of x (x must already be sorted).
    If increasing=False, enforces non-increasing by fitting on -y as increasing and flipping back.
    """
    if len(y) == 0:
        return y

    if increasing:
        return _pav_isotonic_increasing(y, w)
    return -_pav_isotonic_increasing(-y, w)

# =========================
# BINNING + TAIL COLLAPSE
# =========================

def make_base_bins(df: pd.DataFrame, width: float) -> pd.DataFrame:
    """
    Creates base bins on implied_prob_fair.
    Returns one row per bin with:
      band_min, band_max, n, avg_prob, actual_win_rate, delta
    """
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
    g = g.sort_values(["band_min", "band_max"]).reset_index(drop=True)
    return g


def collapse_sparse_tails(bins_df: pd.DataFrame, min_n: int) -> pd.DataFrame:
    """
    Collapses only sparse tails:
      - while first bin n < min_n, merge with next
      - while last  bin n < min_n, merge with previous

    Merge is weighted by n for avg_prob and actual_win_rate.
    """
    if bins_df.empty:
        return bins_df

    bins = bins_df.copy().reset_index(drop=True)

    def merge_rows(a: pd.Series, b: pd.Series) -> pd.Series:
        n1 = float(a["n"])
        n2 = float(b["n"])
        nt = n1 + n2
        if nt <= 0:
            return a

        avg_prob = (a["avg_prob"] * n1 + b["avg_prob"] * n2) / nt
        actual = (a["actual_win_rate"] * n1 + b["actual_win_rate"] * n2) / nt

        out = a.copy()
        out["band_min"] = min(float(a["band_min"]), float(b["band_min"]))
        out["band_max"] = max(float(a["band_max"]), float(b["band_max"]))
        out["n"] = int(nt)
        out["avg_prob"] = float(avg_prob)
        out["actual_win_rate"] = float(actual)
        out["delta"] = float(avg_prob - actual)
        return out

    # Collapse low tail
    while len(bins) >= 2 and int(bins.loc[0, "n"]) < min_n:
        merged = merge_rows(bins.loc[0], bins.loc[1])
        bins = pd.concat([pd.DataFrame([merged]), bins.iloc[2:]], ignore_index=True)

    # Collapse high tail
    while len(bins) >= 2 and int(bins.loc[len(bins) - 1, "n"]) < min_n:
        merged = merge_rows(bins.loc[len(bins) - 2], bins.loc[len(bins) - 1])
        bins = pd.concat([bins.iloc[:-2], pd.DataFrame([merged])], ignore_index=True)

    return bins.reset_index(drop=True)

# =========================
# MAIN
# =========================

def build_side_curve(df_master: pd.DataFrame, market: str) -> pd.DataFrame:
    """
    Build stable monotonic-smoothed delta curve for a single market (home/draw/away).
    Returns bins with extra_juice (smoothed delta) and band ranges.
    """
    sub = df_master[df_master["market"] == market].copy()
    if sub.empty:
        return pd.DataFrame()

    base_bins = make_base_bins(sub, BASE_BUCKET_WIDTH)
    if base_bins.empty:
        return pd.DataFrame()

    # Collapse sparse tails only
    bins = collapse_sparse_tails(base_bins, MIN_SAMPLE)

    # If after collapsing we have 1 bin, just use it (still cap).
    bins = bins.sort_values("avg_prob").reset_index(drop=True)

    x = bins["avg_prob"].to_numpy(dtype=float)
    y = bins["delta"].to_numpy(dtype=float)
    w = bins["n"].to_numpy(dtype=float)

    # Monotonic smoothing on delta vs probability
    if ENFORCE_NONINCREASING:
        y_hat = isotonic_fit(x, y, w, increasing=False)
    else:
        y_hat = isotonic_fit(x, y, w, increasing=True)

    # Cap extremes
    y_hat = np.clip(y_hat, -MAX_ABS_JUICE, MAX_ABS_JUICE)

    out = bins.copy()
    out["extra_juice"] = y_hat

    # Ensure stable ordering by probability band
    out = out.sort_values(["band_min", "band_max"]).reset_index(drop=True)
    return out


def main():
    if not MASTER_FILE.exists():
        print("Calibration master file not found:", MASTER_FILE)
        return

    df = pd.read_csv(MASTER_FILE)

    required = ["league", "market", "implied_prob_fair", "result"]
    if not all(c in df.columns for c in required):
        missing = [c for c in required if c not in df.columns]
        print("Missing required columns:", missing)
        return

    # Filter league and valid probabilities
    df = df[df["league"] == LEAGUE_FILTER].copy()
    df = df.dropna(subset=["market", "implied_prob_fair", "result"])
    df = df[(df["implied_prob_fair"] > 0) & (df["implied_prob_fair"] < 1)]

    if df.empty:
        print("No rows after filtering league/probability.")
        return

    juice_rows = []

    for market in ["1x2_home", "1x2_draw", "1x2_away"]:
        curve = build_side_curve(df, market)
        if curve.empty:
            continue

        side = market.replace("1x2_", "")

        for _, r in curve.iterrows():
            band_min = float(r["band_min"])
            band_max = float(r["band_max"])
            label = f"{band_min:.2f} to {band_max:.2f}"

            juice_rows.append({
                "band": label,
                "band_min": round(band_min, 4),
                "band_max": round(band_max, 4),
                "side": side,
                "extra_juice": float(r["extra_juice"]),
            })

    out = pd.DataFrame(juice_rows)

    if out.empty:
        print("No juice bands generated.")
        return

    # Sort for readability and deterministic output
    side_order = {"home": 0, "draw": 1, "away": 2}
    out["side_sort"] = out["side"].map(side_order).fillna(99).astype(int)
    out = out.sort_values(["side_sort", "band_min", "band_max"]).drop(columns=["side_sort"]).reset_index(drop=True)

    out.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {OUTPUT_FILE} ({len(out)} rows)")
    print(f"Params: BASE_BUCKET_WIDTH={BASE_BUCKET_WIDTH} MIN_SAMPLE={MIN_SAMPLE} MAX_ABS_JUICE={MAX_ABS_JUICE} monotonic_nonincreasing={ENFORCE_NONINCREASING}")


if __name__ == "__main__":
    main()
