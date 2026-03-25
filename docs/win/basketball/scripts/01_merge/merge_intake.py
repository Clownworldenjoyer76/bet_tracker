#!/usr/bin/env python3
# docs/win/basketball/scripts/01_merge/merge_intake.py

import sys
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime

# =========================
# LOGGER UTILITY
# =========================

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

# =========================
# CONSTANTS
# =========================

ROOT_DIR = Path("docs/win/basketball")
INTAKE_DIR = ROOT_DIR / "00_intake"
MERGE_DIR = ROOT_DIR / "01_merge"
ERROR_DIR = ROOT_DIR / "errors/01_merge"

MERGE_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "merge_intake.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {msg}\n")

# =========================
# HELPERS
# =========================

def load_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def build_key(r):
    return (r["game_date"], r["home_team"], r["away_team"])

def build_team_set(r):
    return (r["game_date"], frozenset([r["home_team"], r["away_team"]]))

# =========================
# FIELD STRUCTURE
# =========================

FIELDNAMES = [
    "league","market","game_date","game_time",
    "home_team","away_team","game_id",
    "home_prob","away_prob",
    "away_projected_points","home_projected_points","total_projected_points",
    "away_spread","home_spread","total",
    "away_dk_spread_american","home_dk_spread_american",
    "dk_total_over_american","dk_total_under_american",
    "away_dk_moneyline_american","home_dk_moneyline_american",
]

# =========================
# DISCOVER SLATES
# =========================

prediction_dir = INTAKE_DIR / "predictions"
sportsbook_dir = INTAKE_DIR / "sportsbook"

prediction_files = list(prediction_dir.glob("basketball_*_*.csv"))

slates = []
for f in prediction_files:
    parts = f.stem.split("_")
    league = parts[1]
    slate_date = "_".join(parts[2:])
    slates.append((league, slate_date))

# =========================
# PROCESS
# =========================

for league, slate_date in slates:

    PRED_FILE = prediction_dir / f"basketball_{league}_{slate_date}.csv"
    SPORTSBOOK_FILE = sportsbook_dir / f"basketball_{league}_{slate_date}.csv"
    OUTFILE = MERGE_DIR / f"basketball_{league}_{slate_date}.csv"

    if not PRED_FILE.exists() or not SPORTSBOOK_FILE.exists():
        log(f"{league} {slate_date} missing file. Skipping.")
        continue

    pred_rows = load_rows(PRED_FILE)
    book_rows = load_rows(SPORTSBOOK_FILE)

    # build maps
    pred_map = {build_key(r): r for r in pred_rows}
    book_map = {build_key(r): r for r in book_rows}

    # team-set maps (for detecting flips)
    pred_team_map = {build_team_set(r): r for r in pred_rows}
    book_team_map = {build_team_set(r): r for r in book_rows}

    merged_rows = []

    # =========================
    # MAIN MERGE
    # =========================

    for key, p in pred_map.items():

        # normal match
        if key in book_map:
            d = book_map[key]

        else:
            # check for flipped orientation
            team_key = build_team_set(p)

            if team_key in book_team_map:
                d_raw = book_team_map[team_key]

                log(
                    f"ORIENTATION MISMATCH (swapping) | {league} {slate_date} | "
                    f"PRED: {p['home_team']} vs {p['away_team']} | "
                    f"BOOK: {d_raw['home_team']} vs {d_raw['away_team']}"
                )

                # Book has home/away flipped relative to prediction — swap fields
                d = dict(d_raw)
                d["away_spread"]               = d_raw.get("home_spread", "")
                d["home_spread"]               = d_raw.get("away_spread", "")
                d["away_dk_spread_american"]   = d_raw.get("home_dk_spread_american", "")
                d["home_dk_spread_american"]   = d_raw.get("away_dk_spread_american", "")
                d["away_dk_moneyline_american"] = d_raw.get("home_dk_moneyline_american", "")
                d["home_dk_moneyline_american"] = d_raw.get("away_dk_moneyline_american", "")
                # total/over/under are symmetric — no swap needed

            else:
                log(
                    f"MISSING MATCH | {league} {slate_date} | "
                    f"{p['home_team']} vs {p['away_team']}"
                )
                continue

        game_id = f"{p['game_date']}_{p['away_team']}_{p['home_team']}"

        merged_rows.append({
            "league": p.get("league",""),
            "market": p.get("market",""),
            "game_date": p.get("game_date",""),
            "game_time": d.get("game_time",""),
            "home_team": p.get("home_team",""),
            "away_team": p.get("away_team",""),
            "game_id": game_id,
            "home_prob": p.get("home_prob",""),
            "away_prob": p.get("away_prob",""),
            "away_projected_points": p.get("away_projected_points",""),
            "home_projected_points": p.get("home_projected_points",""),
            "total_projected_points": p.get("total_projected_points",""),
            "away_spread": d.get("away_spread",""),
            "home_spread": d.get("home_spread",""),
            "total": d.get("total",""),
            "away_dk_spread_american": d.get("away_dk_spread_american",""),
            "home_dk_spread_american": d.get("home_dk_spread_american",""),
            "dk_total_over_american": d.get("dk_total_over_american",""),
            "dk_total_under_american": d.get("dk_total_under_american",""),
            "away_dk_moneyline_american": d.get("away_dk_moneyline_american",""),
            "home_dk_moneyline_american": d.get("home_dk_moneyline_american",""),
        })

    if not merged_rows:
        log(f"No matches for {league} {slate_date}")
        continue

    # write
    with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in merged_rows:
            writer.writerow(r)

    log(f"SUCCESS {league} {slate_date} | {len(merged_rows)} rows")

    df = pd.DataFrame(merged_rows)
    audit(LOG_FILE, "MERGE_STAGE", "SUCCESS", f"{league} {slate_date}", df)
