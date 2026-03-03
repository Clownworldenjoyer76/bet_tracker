#!/usr/bin/env python3
# docs/win/hockey/scripts/01_merge/merge_intake.py

import sys
import csv
from pathlib import Path
from datetime import datetime

# =========================
# ARGS
# =========================

if len(sys.argv) != 2:
    raise ValueError("Usage: merge_intake.py YYYY_MM_DD")

slate_date = sys.argv[1].strip()

# =========================
# PATHS
# =========================

INTAKE_DIR = Path("docs/win/hockey/00_intake")

PRED_FILE = INTAKE_DIR / "predictions" / f"hockey_{slate_date}.csv"
SPORTSBOOK_FILE = INTAKE_DIR / "sportsbook" / f"hockey_{slate_date}.csv"

MERGE_DIR = Path("docs/win/hockey/01_merge")
MERGE_DIR.mkdir(parents=True, exist_ok=True)

OUTFILE = MERGE_DIR / f"hockey_{slate_date}.csv"

ERROR_DIR = Path("docs/win/hockey/errors/01_merge")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "merge_intake.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# SAFE INPUT VALIDATION
# =========================

if not PRED_FILE.exists() or not SPORTSBOOK_FILE.exists():
    log(f"No hockey slate found for {slate_date}. Skipping merge.")
    print(f"No hockey slate found for {slate_date}. Skipping.")
    sys.exit(0)

# =========================
# LOAD
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

pred_data = load_dedupe(PRED_FILE, key_fields)
dk_data = load_dedupe(SPORTSBOOK_FILE, key_fields)

# =========================
# FIELDNAMES
# =========================

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
    "away_projected_goals",
    "home_projected_goals",
    "total_projected_goals",
    "away_puck_line",
    "home_puck_line",
    "total",
    "away_dk_puck_line_american",
    "home_dk_puck_line_american",
    "dk_total_over_american",
    "dk_total_under_american",
    "away_dk_moneyline_american",
    "home_dk_moneyline_american",
]

# =========================
# MERGE (FULL REBUILD)
# =========================

merged_rows = []

for key, p in pred_data.items():

    if key not in dk_data:
        continue

    d = dk_data[key]

    if d.get("home_team") != p.get("home_team") or d.get("away_team") != p.get("away_team"):
        log(f"TEAM MISMATCH: {p.get('home_team')} vs {p.get('away_team')}")
        continue

    try:
        home_pl = float(d.get("home_puck_line", 0))
        away_pl = float(d.get("away_puck_line", 0))
        if home_pl != -away_pl:
            log(f"PUCK LINE IMBALANCE: {p.get('home_team')} vs {p.get('away_team')}")
    except:
        pass

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
        "away_projected_goals": p.get("away_projected_goals", ""),
        "home_projected_goals": p.get("home_projected_goals", ""),
        "total_projected_goals": p.get("total_projected_goals", ""),
        "away_puck_line": d.get("away_puck_line", ""),
        "home_puck_line": d.get("home_puck_line", ""),
        "total": d.get("total", ""),
        "away_dk_puck_line_american": d.get("away_dk_puck_line_american", ""),
        "home_dk_puck_line_american": d.get("home_dk_puck_line_american", ""),
        "dk_total_over_american": d.get("dk_total_over_american", ""),
        "dk_total_under_american": d.get("dk_total_under_american", ""),
        "away_dk_moneyline_american": d.get("away_dk_moneyline_american", ""),
        "home_dk_moneyline_american": d.get("home_dk_moneyline_american", ""),
    })

if not merged_rows:
    log(f"No matching rows to merge for slate {slate_date}.")
    print(f"No matching rows to merge for slate {slate_date}.")
    sys.exit(0)

# =========================
# ATOMIC WRITE (REBUILD)
# =========================

temp_file = OUTFILE.with_suffix(".tmp")

with open(temp_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for r in sorted(merged_rows, key=lambda x: (x["game_date"], x["game_time"], x["home_team"])):
        writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

temp_file.replace(OUTFILE)

log(f"SUMMARY: rebuilt {len(merged_rows)} games for slate {slate_date}")
print(f"Wrote {OUTFILE}")
