#!/usr/bin/env python3
# docs/win/hockey/scripts/01_merge/merge_intake.py

import sys
import csv
from pathlib import Path
from datetime import datetime

# =========================
# PATHS
# =========================

INTAKE_DIR = Path("docs/win/hockey/00_intake")
PRED_DIR = INTAKE_DIR / "predictions"
SPORTSBOOK_DIR = INTAKE_DIR / "sportsbook"

MERGE_DIR = Path("docs/win/hockey/01_merge")
MERGE_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = Path("docs/win/hockey/errors/01_merge")
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
    duplicates = 0

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = tuple(r[k] for k in key_fields)
            if key in data:
                duplicates += 1
            data[key] = r

    return data, duplicates

key_fields = ["game_date", "home_team", "away_team"]

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
# AUTO DISCOVER SLATES
# =========================

prediction_files = list(PRED_DIR.glob("hockey_*.csv"))

if not prediction_files:
    log("No prediction files found.")
    print("No hockey prediction files found.")
    sys.exit(0)

# =========================
# PROCESS EACH SLATE
# =========================

for pred_file in prediction_files:

    slate_date = pred_file.stem.replace("hockey_", "")

    PRED_FILE = PRED_DIR / f"hockey_{slate_date}.csv"
    SPORTSBOOK_FILE = SPORTSBOOK_DIR / f"hockey_{slate_date}.csv"
    OUTFILE = MERGE_DIR / f"hockey_{slate_date}.csv"

    if not PRED_FILE.exists() or not SPORTSBOOK_FILE.exists():
        log(f"MISSING FILE: slate={slate_date} predictions_or_sportsbook_missing")
        print(f"No hockey slate found for {slate_date}. Skipping.")
        continue

    pred_data, pred_dupes = load_dedupe(PRED_FILE, key_fields)
    dk_data, book_dupes = load_dedupe(SPORTSBOOK_FILE, key_fields)

    pred_count = len(pred_data)
    book_count = len(dk_data)

    if pred_dupes > 0:
        log(f"PREDICTION DUPLICATES: slate={slate_date} count={pred_dupes}")

    if book_dupes > 0:
        log(f"SPORTSBOOK DUPLICATES: slate={slate_date} count={book_dupes}")

    # =========================
    # MERGE (FULL REBUILD)
    # =========================

    merged_rows = []
    missing_keys = 0

    for key, p in pred_data.items():

        if key not in dk_data:
            missing_keys += 1
            log(f"MISSING MATCH: slate={slate_date} {p.get('away_team')} @ {p.get('home_team')}")
            continue

        d = dk_data[key]

        if d.get("home_team") != p.get("home_team") or d.get("away_team") != p.get("away_team"):
            log(f"TEAM MISMATCH: slate={slate_date} {p.get('away_team')} @ {p.get('home_team')}")
            continue

        # Puck line validation
        try:
            home_pl = float(d.get("home_puck_line", 0))
            away_pl = float(d.get("away_puck_line", 0))
            if home_pl != -away_pl:
                log(
                    f"PUCK LINE IMBALANCE: slate={slate_date} "
                    f"{p.get('away_team')} @ {p.get('home_team')} "
                    f"home={home_pl} away={away_pl}"
                )
        except:
            log(f"PUCK LINE PARSE ERROR: slate={slate_date} {p.get('away_team')} @ {p.get('home_team')}")

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

    merged_count = len(merged_rows)

    # =========================
    # DUPLICATE CHECK (MERGED OUTPUT)
    # =========================

    seen = set()
    dupes = 0

    for r in merged_rows:
        if r["game_id"] in seen:
            dupes += 1
        seen.add(r["game_id"])

    if dupes > 0:
        log(f"MERGE DUPLICATES: slate={slate_date} count={dupes}")

    # =========================
    # EMPTY MERGE CHECK
    # =========================

    if not merged_rows:
        log(f"EMPTY MERGE: slate={slate_date}")
        print(f"No matching rows to merge for slate {slate_date}.")
        continue

    # =========================
    # SUMMARY LOGGING (CRITICAL)
    # =========================

    log(
        f"SUMMARY: slate={slate_date} "
        f"pred={pred_count} book={book_count} merged={merged_count} dropped={missing_keys}"
    )

    # =========================
    # ATOMIC WRITE (REBUILD)
    # =========================

    temp_file = OUTFILE.with_suffix(".tmp")

    with open(temp_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for r in sorted(
            merged_rows,
            key=lambda x: (x["game_date"], x["game_time"], x["home_team"])
        ):
            writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

    temp_file.replace(OUTFILE)

    print(f"Wrote {OUTFILE}")
