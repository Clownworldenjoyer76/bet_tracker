#!/usr/bin/env python3

import csv
import math
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

EDGE_DIR = Path("docs/win/edge")
DK_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

# ============================================================
# CONSTANTS
# ============================================================

SIGMA = 7.2
P_MIN = 1e-6
P_MAX = 1.0 - 1e-6

# ============================================================
# MATH / ODDS HELPERS
# ============================================================

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def clamp(p: float) -> float:
    return max(P_MIN, min(P_MAX, p))

def american_to_decimal(a: float) -> float:
    if a > 0:
        return 1.0 + (a / 100.0)
    return 1.0 + (100.0 / abs(a))

def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

def decimal_to_prob(d: float) -> float:
    return 1.0 / d

def american_to_prob(a: float) -> float:
    return decimal_to_prob(american_to_decimal(a))

# ============================================================
# JUICE TABLE (OPTIONAL ADJUSTMENT)
# ============================================================

def load_spreads_juice_table(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "low": float(r["band_low"]),
                "high": float(r["band_high"]),
                "side": r["side"].lower(),
                "juice": float(r["extra_juice_pct"]),
            })
    return rows

def lookup_spreads_juice(table, spread_abs, side):
    for r in table:
        if r["low"] <= spread_abs <= r["high"]:
            if r["side"] == "any" or r["side"] == side:
                return r["juice"]
    return 0.0

# ============================================================
# DK ODDS COLUMN DETECTION
# ============================================================

def pick_odds_columns(fieldnames):
    """
    Returns (american_col, decimal_col) where either can be None.
    We do not assume exact names; we detect by header substrings.
    """
    f = [x.strip() for x in fieldnames if x]
    f_lower = [x.lower() for x in f]

    def find_any(preds):
        for p in preds:
            for i, name in enumerate(f_lower):
                if p(name):
                    return f[i]
        return None

    # American odds candidates (most specific first)
    american_col = find_any([
        lambda s: s == "american_odds",
        lambda s: s.endswith("american_odds"),
        lambda s: ("american" in s and "odds" in s),
        lambda s: s in ("odds_american", "american", "price_american"),
        lambda s: ("moneyline" in s and "american" in s),
    ])

    # Decimal odds candidates
    decimal_col = find_any([
        lambda s: s == "decimal_odds",
        lambda s: s.endswith("decimal_odds"),
        lambda s: ("decimal" in s and "odds" in s),
        lambda s: s in ("odds_decimal", "decimal", "price_decimal"),
    ])

    # If nothing matched, try a very broad fallback for odds/price
    if american_col is None and decimal_col is None:
        decimal_col = find_any([
            lambda s: s == "odds",
            lambda s: s == "price",
            lambda s: s.endswith("_odds"),
            lambda s: s.endswith("_price"),
        ])

    return american_col, decimal_col

def parse_float_maybe(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None

# ============================================================
# MAIN
# ============================================================

def main():
    dk_files = sorted(DK_DIR.glob("norm_dk_ncaab_spreads_*.csv"))
    edge_files = sorted(EDGE_DIR.glob("edge_ncaab_*.csv"))
    if not dk_files:
        raise RuntimeError("No DK spreads files found in docs/win/manual/normalized/")
    if not edge_files:
        raise RuntimeError("No edge model files found in docs/win/edge/")

    dk_file = dk_files[-1]
    edge_file = edge_files[-1]

    # extract date from DK filename: norm_dk_ncaab_spreads_YYYY_MM_DD.csv
    parts = dk_file.stem.split("_")
    yyyy, mm, dd = parts[-3], parts[-2], parts[-1]
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{yyyy}_{mm}_{dd}.csv"

    # ------------------------
    # load edge model
    # ------------------------
    model_by_team = {}
    game_meta = {}

    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            team = r["team"].strip()
            model_by_team[team] = r
            game_meta[team] = {
                "game_id": r["game_id"],
                "date": r["date"],
                "time": r["time"],
                "opponent": r["opponent"].strip(),
                "points": float(r["points"]),
            }

    # ------------------------
    # load juice table (used only as optional market-prob adjustment)
    # ------------------------
    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    fields = [
        "game_id",
        "date",
        "time",
        "team",
        "opponent",
        "spread",
        "model_probability",
        "dk_odds_type",
        "dk_decimal_odds",
        "dk_american_odds",
        "market_implied_prob",
        "market_implied_prob_juiced",
        "edge_prob",
        "edge_pct",
        "league",
    ]

    rows_written = 0

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        w = csv.DictWriter(f_out, fieldnames=fields)
        w.writeheader()

        with dk_file.open(newline="", encoding="utf-8") as dk:
            reader = csv.DictReader(dk)
            if not reader.fieldnames:
                raise RuntimeError(f"DK file has no header: {dk_file}")

            american_col, decimal_col = pick_odds_columns(reader.fieldnames)

            for r in reader:
                team = (r.get("team") or "").strip()
                if not team or team not in model_by_team:
                    continue

                meta = game_meta[team]
                opp = meta["opponent"]
                if opp not in model_by_team:
                   
