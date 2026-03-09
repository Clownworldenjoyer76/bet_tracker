#!/usr/bin/env python3

import csv
import sys
from pathlib import Path
from datetime import datetime
from bisect import bisect_left

# =========================
# PATHS
# =========================

MERGE_DIR = Path("docs/win/soccer/01_merge")
OUT_DIR = MERGE_DIR / "market_model"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_BASE = Path("config/soccer")

ERROR_DIR = Path("docs/win/soccer/errors/01_merge")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "market_model.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


# =========================
# CONFIG MAP
# =========================

CONFIG_MAP = {
    "bundesliga": "bundesliga",
    "epl": "epl",
    "laliga": "la_liga",
    "ligue1": "ligue1",
    "seriea": "serie_a",
}

# DC table cache
DC_CACHE = {}


# =========================
# LOAD DC TABLE
# =========================

def load_dc_table(path):

    rows = []
    lambda_home_vals = set()
    lambda_away_vals = set()

    with open(path, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for r in reader:

            try:
                lh = float(r["lambda_home"])
                la = float(r["lambda_away"])

                rows.append({
                    "lambda_home": lh,
                    "lambda_away": la,
                    "home_win": float(r["home_win"]),
                    "draw": float(r["draw"]),
                    "away_win": float(r["away_win"]),
                    "over2_5": float(r["over2_5"]),
                    "btts_yes": float(r["btts_yes"]),
                })

                lambda_home_vals.add(lh)
                lambda_away_vals.add(la)

            except:
                continue

    lambda_home_vals = sorted(lambda_home_vals)
    lambda_away_vals = sorted(lambda_away_vals)

    return rows, lambda_home_vals, lambda_away_vals


# =========================
# GET DC TABLE (cached)
# =========================

def get_dc_table(market):

    if market in DC_CACHE:
        return DC_CACHE[market]

    config_dir = CONFIG_BASE / CONFIG_MAP[market]
    dc_file = config_dir / "dc_soccer_pricing_engine.csv"

    if not dc_file.exists():
        log(f"Missing config file: {dc_file}")
        return None

    rows, lh_vals, la_vals = load_dc_table(dc_file)

    DC_CACHE[market] = (rows, lh_vals, la_vals)

    return DC_CACHE[market]


# =========================
# FIND CLOSEST GRID VALUES
# =========================

def find_bounds(values, x):

    pos = bisect_left(values, x)

    if pos == 0:
        return values[0], values[0]

    if pos >= len(values):
        return values[-1], values[-1]

    return values[pos-1], values[pos]


# =========================
# LOOKUP GRID VALUE
# =========================

def find_row(table, lh, la):

    for r in table:
        if r["lambda_home"] == lh and r["lambda_away"] == la:
            return r

    return None


# =========================
# BILINEAR INTERPOLATION
# =========================

def interpolate(table, lh_vals, la_vals, lh, la):

    lh0, lh1 = find_bounds(lh_vals, lh)
    la0, la1 = find_bounds(la_vals, la)

    q11 = find_row(table, lh0, la0)
    q12 = find_row(table, lh0, la1)
    q21 = find_row(table, lh1, la0)
    q22 = find_row(table, lh1, la1)

    if not all([q11, q12, q21, q22]):
        return q11 or q12 or q21 or q22

    def interp(v11, v12, v21, v22):

        if lh1 == lh0 or la1 == la0:
            return v11

        return (
            v11 * (lh1 - lh) * (la1 - la) +
            v21 * (lh - lh0) * (la1 - la) +
            v12 * (lh1 - lh) * (la - la0) +
            v22 * (lh - lh0) * (la - la0)
        ) / ((lh1 - lh0) * (la1 - la0))

    return {
        "home_win": interp(q11["home_win"], q12["home_win"], q21["home_win"], q22["home_win"]),
        "draw": interp(q11["draw"], q12["draw"], q21["draw"], q22["draw"]),
        "away_win": interp(q11["away_win"], q12["away_win"], q21["away_win"], q22["away_win"]),
        "over2_5": interp(q11["over2_5"], q12["over2_5"], q21["over2_5"], q22["over2_5"]),
        "btts_yes": interp(q11["btts_yes"], q12["btts_yes"], q21["btts_yes"], q22["btts_yes"]),
    }


# =========================
# OUTPUT FIELDS
# =========================

FIELDNAMES = [
    "game_id",
    "market",
    "home_team",
    "away_team",
    "lambda_home",
    "lambda_away",
    "home_win_prob",
    "draw_prob",
    "away_win_prob",
    "over25_prob",
    "btts_prob",
]


# =========================
# PROCESS MERGE FILES
# =========================

merge_files = list(MERGE_DIR.glob("soccer_*.csv"))

if not merge_files:
    print("No merge files found.")
    sys.exit(0)


for merge_file in merge_files:

    slate_date = merge_file.stem.replace("soccer_", "")

    outfile = OUT_DIR / f"soccer_{slate_date}.csv"

    rows = []

    with open(merge_file, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for r in reader:

            market = r["market"]

            if market not in CONFIG_MAP:
                log(f"Unknown market: {market}")
                continue

            table_data = get_dc_table(market)

            if not table_data:
                continue

            table, lh_vals, la_vals = table_data

            try:
                lh = float(r["home_xg"])
                la = float(r["away_xg"])
            except:
                log(f"Invalid xG for {r.get('game_id','UNKNOWN')}")
                continue

            dc_row = interpolate(table, lh_vals, la_vals, lh, la)

            if not dc_row:
                log(f"No DC row found for {r['game_id']}")
                continue

            rows.append({
                "game_id": r["game_id"],
                "market": market,
                "home_team": r["home_team"],
                "away_team": r["away_team"],
                "lambda_home": lh,
                "lambda_away": la,
                "home_win_prob": dc_row["home_win"],
                "draw_prob": dc_row["draw"],
                "away_win_prob": dc_row["away_win"],
                "over25_prob": dc_row["over2_5"],
                "btts_prob": dc_row["btts_yes"],
            })

    if not rows:
        log(f"No model rows for slate {slate_date}")
        continue

    with open(outfile, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {outfile} ({len(rows)} rows)")
    log(f"SUMMARY: wrote {len(rows)} rows for slate {slate_date}")
