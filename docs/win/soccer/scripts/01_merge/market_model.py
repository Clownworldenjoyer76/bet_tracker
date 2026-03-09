#!/usr/bin/env python3

import csv
import sys
from pathlib import Path
from datetime import datetime

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

# cache for DC tables
DC_CACHE = {}


# =========================
# HELPERS
# =========================

def load_dc_table(path):

    rows = []

    with open(path, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for r in reader:

            try:
                rows.append({
                    "lambda_home": float(r["lambda_home"]),
                    "lambda_away": float(r["lambda_away"]),
                    "home_win": float(r["home_win"]),
                    "draw": float(r["draw"]),
                    "away_win": float(r["away_win"]),
                    "over2_5": float(r["over2_5"]),
                    "btts_yes": float(r["btts_yes"]),
                })
            except Exception:
                continue

    return rows


def get_dc_table(market):

    if market in DC_CACHE:
        return DC_CACHE[market]

    config_dir = CONFIG_BASE / CONFIG_MAP[market]
    dc_file = config_dir / "dc_soccer_pricing_engine.csv"

    if not dc_file.exists():
        log(f"Missing config file: {dc_file}")
        return None

    table = load_dc_table(dc_file)

    DC_CACHE[market] = table

    return table


def closest_row(table, lh, la):

    best = None
    best_dist = float("inf")

    for r in table:

        # Euclidean distance (prevents lambda swapping issue)
        dist = (r["lambda_home"] - lh) ** 2 + (r["lambda_away"] - la) ** 2

        if dist < best_dist:
            best_dist = dist
            best = r

    return best


# =========================
# FIELDNAMES
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
# LOAD MERGE FILES
# =========================

merge_files = list(MERGE_DIR.glob("soccer_*.csv"))

if not merge_files:
    print("No merge files found.")
    sys.exit(0)


# =========================
# PROCESS SLATES
# =========================

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

            dc_table = get_dc_table(market)

            if not dc_table:
                continue

            try:
                lh = float(r["home_xg"])
                la = float(r["away_xg"])
            except Exception:
                log(f"Invalid xG for {r.get('game_id','UNKNOWN')}")
                continue

            dc_row = closest_row(dc_table, la, lh)

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
