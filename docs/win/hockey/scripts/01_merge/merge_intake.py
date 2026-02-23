# docs/win/hockey/scripts/01_merge/merge_intake.py

#!/usr/bin/env python3

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

# reset log each run
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# VALIDATE INPUT FILES
# =========================

if not PRED_FILE.exists():
    raise FileNotFoundError(f"Missing predictions file: {PRED_FILE}")

if not SPORTSBOOK_FILE.exists():
    raise FileNotFoundError(f"Missing sportsbook file: {SPORTSBOOK_FILE}")

# =========================
# LOAD + DEDUPE
# =========================

def load_dedupe(path, key_fields):
    data = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = tuple(r[k] for k in key_fields)
            data[key] = r  # overwrite duplicates
    return data

key_fields = ["game_date", "home_team", "away_team"]

pred_data = load_dedupe(PRED_FILE, key_fields)
dk_data = load_dedupe(SPORTSBOOK_FILE, key_fields)

# =========================
# FIELDNAMES
# =========================

FIELDNAMES = [
    "league",
    "bet_type",
    "game_date",
    "game_time",
    "home_team",
    "away_team",
    "game_id",

    # model
    "home_prob",
    "away_prob",
    "away_projected_goals",
    "home_projected_goals",
    "total_projected_goals",

    # sportsbook lines
    "away_puck_line",
    "home_puck_line",
    "total",

    # sportsbook odds
    "away_dk_puck_line_american",
    "home_dk_puck_line_american",
    "dk_total_over_american",
    "dk_total_under_american",
    "away_dk_moneyline_american",
    "home_dk_moneyline_american",
]

# =========================
# MERGE
# =========================

merged_rows = {}

for key, p in pred_data.items():

    if key not in dk_data:
        continue  # AND-only behavior

    d = dk_data[key]

    game_id = f"{p['game_date']}_{p['home_team']}_{p['away_team']}"

    base = {
        "league": p["league"],
        "game_date": p["game_date"],
        "game_time": p["game_time"],
        "home_team": p["home_team"],
        "away_team": p["away_team"],
        "game_id": game_id,
    }

    # ---------------------
    # MONEYLINE ROW
    # ---------------------
    ml_key = (p["game_date"], "moneyline", p["home_team"], p["away_team"])

    merged_rows[ml_key] = {
        **base,
        "bet_type": "moneyline",

        "home_prob": p.get("home_prob", ""),
        "away_prob": p.get("away_prob", ""),

        "away_dk_moneyline_american": d.get("away_dk_moneyline_american", ""),
        "home_dk_moneyline_american": d.get("home_dk_moneyline_american", ""),
    }

    # ---------------------
    # TOTALS ROW
    # ---------------------
    total_key = (p["game_date"], "totals", p["home_team"], p["away_team"])

    merged_rows[total_key] = {
        **base,
        "bet_type": "totals",

        "total_projected_goals": p.get("total_projected_goals", ""),

        "total": d.get("total", ""),
        "dk_total_over_american": d.get("dk_total_over_american", ""),
        "dk_total_under_american": d.get("dk_total_under_american", ""),
    }

    # ---------------------
    # PUCK LINE ROW
    # ---------------------
    pl_key = (p["game_date"], "puck_line", p["home_team"], p["away_team"])

    merged_rows[pl_key] = {
        **base,
        "bet_type": "puck_line",

        "away_puck_line": d.get("away_puck_line", ""),
        "home_puck_line": d.get("home_puck_line", ""),

        "away_dk_puck_line_american": d.get("away_dk_puck_line_american", ""),
        "home_dk_puck_line_american": d.get("home_dk_puck_line_american", ""),
    }

# =========================
# LOAD EXISTING (UPSERT SAFE)
# =========================

existing = {}

if OUTFILE.exists():
    with open(OUTFILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames == FIELDNAMES:
            for r in reader:
                key = (
                    r["game_date"],
                    r["bet_type"],
                    r["home_team"],
                    r["away_team"],
                )
                existing[key] = r
        else:
            log("WARNING: Header mismatch detected. Rebuilding clean.")

# upsert
for key, row in merged_rows.items():
    existing[key] = row

# =========================
# ATOMIC WRITE
# =========================

temp_file = OUTFILE.with_suffix(".tmp")

with open(temp_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for r in existing.values():
        writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

temp_file.replace(OUTFILE)

log(f"SUMMARY: merged {len(merged_rows)} rows for slate {slate_date}")
print(f"Wrote {OUTFILE}")
