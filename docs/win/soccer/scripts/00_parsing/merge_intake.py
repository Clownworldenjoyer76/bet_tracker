#!/usr/bin/env python3

import sys
import csv
from pathlib import Path
from datetime import datetime

ERROR_DIR = Path("docs/win/soccer/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "merge_intake_log.txt"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

league = sys.argv[1].strip()
market = sys.argv[2].strip()

BASE_DIR = Path("docs/win/soccer/00_intake")
SPORTSBOOK_DIR = BASE_DIR / "sportsbook"
PRED_DIR = BASE_DIR / "predictions"

def latest(d, prefix):
    files = sorted(d.glob(f"{prefix}_*.csv"), key=lambda x: x.stat().st_mtime)
    if not files:
        raise FileNotFoundError("Missing intake files")
    return files[-1]

dk_file = latest(SPORTSBOOK_DIR, f"{market}_dk")
pred_file = latest(PRED_DIR, f"{market}_pred")

dk_data = {}

with open(dk_file, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        dk_data[(r["home_team"], r["away_team"])] = r

rows = []
match_date = None

with open(pred_file, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        key = (r["home_team"], r["away_team"])
        if key not in dk_data:
            continue
        match_date = r["match_date"]
        rows.append([
            r["league"],
            r["market"],
            r["match_date"],
            r["match_time"],
            r["home_team"],
            r["away_team"],
            r["home_prob"],
            r["draw_prob"],
            r["away_prob"],
            dk_data[key]["dk_home_american"],
            dk_data[key]["dk_draw_american"],
            dk_data[key]["dk_away_american"],
            f"{r['league']}_{r['market']}_{r['match_date']}_{r['home_team']}_{r['away_team']}",
        ])

outfile = BASE_DIR / f"{match_date}_{league}_{market}.csv"
write_header = not outfile.exists()

with open(outfile, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    if write_header:
        writer.writerow([
            "league","market","match_date","match_time",
            "home_team","away_team",
            "home_prob","draw_prob","away_prob",
            "home_american","draw_american","away_american","game_id"
        ])
    writer.writerows(rows)

log(f"SUMMARY: appended {len(rows)} rows to {outfile}")
print(f"Updated {outfile}")
