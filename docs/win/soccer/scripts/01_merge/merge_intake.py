# docs/win/soccer/scripts/01_merge/merge_intake.py
#!/usr/bin/env python3

import sys
import csv
from pathlib import Path
from datetime import datetime

# =========================
# PATHS
# =========================

INTAKE_DIR = Path("docs/win/soccer/00_intake")

SPORTSBOOK_DIR = INTAKE_DIR / "sportsbook" / "combined"
PRED_DIR = INTAKE_DIR / "predictions" / "combined"

MERGE_DIR = Path("docs/win/soccer/01_merge")
MERGE_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = Path("docs/win/soccer/errors/01_merge")
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

# =========================
# FIELDNAMES
# =========================

FIELDNAMES = [
    "league","market","match_date","match_time",
    "home_team","away_team",
    "home_prob","draw_prob","away_prob",
    "home_xg","away_xg","expected_total_goals",
    "home_american","draw_american","away_american",
    "game_id"
]

# =========================
# AUTO DISCOVER SLATES
# =========================

prediction_files = list(PRED_DIR.glob("soccer_*.csv"))

if not prediction_files:
    log("No soccer prediction files found.")
    print("No soccer prediction files found.")
    sys.exit(0)

# =========================
# PROCESS EACH SLATE
# =========================

for pred_file in prediction_files:

    slate_date = pred_file.stem.replace("soccer_", "")

    SPORTSBOOK_FILE = SPORTSBOOK_DIR / f"soccer_{slate_date}.csv"
    PRED_FILE = PRED_DIR / f"soccer_{slate_date}.csv"

    OUTFILE = MERGE_DIR / f"soccer_{slate_date}.csv"

    if not SPORTSBOOK_FILE.exists():
        log(f"Missing sportsbook file: {SPORTSBOOK_FILE}")
        print(f"No soccer sportsbook file for {slate_date}. Skipping.")
        continue

    if not PRED_FILE.exists():
        log(f"Missing predictions file: {PRED_FILE}")
        print(f"No soccer predictions file for {slate_date}. Skipping.")
        continue

    # =========================
    # LOAD + DEDUPE
    # =========================

    pred_key_fields = ["match_date", "market", "home_team", "away_team"]
    dk_key_fields = ["match_date", "market", "home_team", "away_team"]

    pred_data = load_dedupe(PRED_FILE, pred_key_fields)
    dk_data = load_dedupe(SPORTSBOOK_FILE, dk_key_fields)

    # =========================
    # MERGE
    # =========================

    merged_rows = {}

    for key, p in pred_data.items():

        if key not in dk_data:
            continue

        d = dk_data[key]

        game_id = f"{p['match_date']}_{p['home_team']}_{p['away_team']}"

        merged_rows[key] = {
            "league": p["league"],
            "market": p["market"],
            "match_date": p["match_date"],
            "match_time": p["match_time"],

            "home_team": p["home_team"],
            "away_team": p["away_team"],

            "home_prob": p["home_prob"],
            "draw_prob": p["draw_prob"],
            "away_prob": p["away_prob"],

            "home_xg": p.get("home_xg",""),
            "away_xg": p.get("away_xg",""),
            "expected_total_goals": p.get("expected_total_goals",""),

            "home_american": d["dk_home_american"],
            "draw_american": d["dk_draw_american"],
            "away_american": d["dk_away_american"],

            "game_id": game_id,
        }

    if not merged_rows:
        log(f"No matching rows to merge for slate {slate_date}.")
        print(f"No matching rows to merge for slate {slate_date}.")
        continue

    # =========================
    # LOAD EXISTING
    # =========================

    existing = {}

    if OUTFILE.exists():

        with open(OUTFILE, newline="", encoding="utf-8") as f:

            reader = csv.DictReader(f)

            if reader.fieldnames == FIELDNAMES:

                for r in reader:

                    key = (
                        r["match_date"],
                        r["market"],
                        r["home_team"],
                        r["away_team"],
                    )

                    existing[key] = r

    # =========================
    # UPSERT
    # =========================

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
