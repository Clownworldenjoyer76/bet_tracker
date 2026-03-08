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
    
    # 1. EXHAUSTIVE LOG (TXT)
    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

    # 2. CONDENSED SUMMARY (TXT)
    if df is not None and isinstance(df, pd.DataFrame):
        summary_path = log_path.parent / "condensed_summary.txt"
        
        play_cols = [c for c in ['home_play', 'away_play', 'over_play', 'under_play'] if c in df.columns]
        
        if play_cols:
            signals = df[df[play_cols].any(axis=1)].copy()
            
            if not signals.empty:
                with open(summary_path, "a") as f:
                    f.write(f"\n--- BETTING SIGNALS: {ts} ---\n")
                    base_cols = ['game_date', 'home_team', 'away_team']
                    edge_cols = [c for c in df.columns if 'edge_pct' in c]
                    
                    final_cols = [c for c in base_cols + edge_cols if c in signals.columns]
                    f.write(signals[final_cols].to_string(index=False))
                    f.write("\n" + "="*30 + "\n")

# =========================
# CONSTANTS
# =========================

LEAGUES = ["NBA", "NCAAB"]

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
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# HELPERS
# =========================

def load_dedupe(path, key_fields):
    data = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = tuple(r[k] for k in key_fields)
            data[key] = r
    return data

key_fields = ["game_date", "home_team", "away_team"]

FIELDNAMES = [
    "league",
    "market",
    "game_date",
    "game_time",
    "home_team",
    "away_team",
    "game_id",
    "home_prob",
    "away_prob",
    "away_projected_points",
    "home_projected_points",
    "total_projected_points",
    "away_spread",
    "home_spread",
    "total",
    "away_dk_spread_american",
    "home_dk_spread_american",
    "dk_total_over_american",
    "dk_total_under_american",
    "away_dk_moneyline_american",
    "home_dk_moneyline_american",
]

# =========================
# AUTO DISCOVER SLATES
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
# PROCESS EACH SLATE
# =========================

for league, slate_date in slates:

    PRED_FILE = prediction_dir / f"basketball_{league}_{slate_date}.csv"
    SPORTSBOOK_FILE = sportsbook_dir / f"basketball_{league}_{slate_date}.csv"
    OUTFILE = MERGE_DIR / f"basketball_{league}_{slate_date}.csv"

    if not PRED_FILE.exists() or not SPORTSBOOK_FILE.exists():
        log(f"No {league} sportsbook or prediction file for {slate_date}. Skipping merge.")
        print(f"No {league} slate found for {slate_date}. Skipping.")
        continue

    pred_data = load_dedupe(PRED_FILE, key_fields)
    dk_data = load_dedupe(SPORTSBOOK_FILE, key_fields)

    merged_rows = []

    for key, p in pred_data.items():

        if key not in dk_data:
            continue

        d = dk_data[key]

        if d.get("home_team") != p.get("home_team") or d.get("away_team") != p.get("away_team"):
            log(f"{league} TEAM MISMATCH: {p.get('home_team')} vs {p.get('away_team')}")
            continue

        game_id = f"{p['game_date']}_{p['away_team']}_{p['home_team']}"

        merged_rows.append({
            "league": p.get("league", ""),
            "market": p.get("market", ""),
            "game_date": p.get("game_date", ""),
            "game_time": p.get("game_time", ""),
            "home_team": p.get("home_team", ""),
            "away_team": p.get("away_team", ""),
            "game_id": game_id,
            "home_prob": p.get("home_prob", ""),
            "away_prob": p.get("away_prob", ""),
            "away_projected_points": p.get("away_projected_points", ""),
            "home_projected_points": p.get("home_projected_points", ""),
            "total_projected_points": p.get("total_projected_points", ""),
            "away_spread": d.get("away_spread", ""),
            "home_spread": d.get("home_spread", ""),
            "total": d.get("total", ""),
            "away_dk_spread_american": d.get("away_dk_spread_american", ""),
            "home_dk_spread_american": d.get("home_dk_spread_american", ""),
            "dk_total_over_american": d.get("dk_total_over_american", ""),
            "dk_total_under_american": d.get("dk_total_under_american", ""),
            "away_dk_moneyline_american": d.get("away_dk_moneyline_american", ""),
            "home_dk_moneyline_american": d.get("home_dk_moneyline_american", ""),
        })

    if not merged_rows:
        log(f"No matching {league} rows to merge for slate {slate_date}.")
        print(f"No matching {league} rows to merge for slate {slate_date}.")
        continue

    temp_file = OUTFILE.with_suffix(".tmp")

    with open(temp_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in sorted(merged_rows, key=lambda x: (x["game_date"], x["game_time"], x["home_team"])):
            writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

    temp_file.replace(OUTFILE)

    log(f"SUMMARY: rebuilt {len(merged_rows)} {league} games for slate {slate_date}")
    print(f"Wrote {OUTFILE}")

    df_merged = pd.DataFrame(merged_rows)
    audit(LOG_FILE, "MERGE_STAGE", "SUCCESS", msg=f"Merged {league} data", df=df_merged)
