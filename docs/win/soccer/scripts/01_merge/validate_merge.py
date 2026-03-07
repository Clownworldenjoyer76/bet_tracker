#!/usr/bin/env python3

import sys
import csv
from pathlib import Path
from datetime import datetime

# =========================
# ARGS
# =========================

if len(sys.argv) != 2:
    raise ValueError("Usage: validate_merge.py YYYY_MM_DD")

slate_date = sys.argv[1].strip()

# =========================
# PATHS
# =========================

MERGE_FILE = Path(f"docs/win/soccer/01_merge/soccer_{slate_date}.csv")

ERROR_DIR = Path("docs/win/soccer/errors/01_merge")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "validate_merge.txt"

# overwrite log each run
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# VALIDATION
# =========================

if not MERGE_FILE.exists():
    raise FileNotFoundError(f"Missing merge file: {MERGE_FILE}")

required_fields = [
    "league","market","match_date","match_time",
    "home_team","away_team",
    "home_prob","draw_prob","away_prob",
    "home_xg","away_xg","expected_total_goals",
    "home_american","draw_american","away_american",
    "game_id"
]

rows_checked = 0
errors = 0
game_ids = set()

with open(MERGE_FILE, newline="", encoding="utf-8") as f:

    reader = csv.DictReader(f)

    # -------------------------
    # HEADER VALIDATION
    # -------------------------

    for field in required_fields:
        if field not in reader.fieldnames:
            log(f"ERROR: Missing required column {field}")
            raise ValueError("Invalid header structure")

    # -------------------------
    # ROW VALIDATION
    # -------------------------

    for r in reader:

        rows_checked += 1

        # Check probability sum
        try:
            hp = float(r["home_prob"])
            dp = float(r["draw_prob"])
            ap = float(r["away_prob"])
        except Exception:
            log(f"ERROR: Invalid probability format in row {rows_checked}")
            errors += 1
            continue

        total = hp + dp + ap

        if abs(total - 1.0) > 0.02:
            log(f"ERROR: Prob sum != 1.0 ({total}) in row {rows_checked}")
            errors += 1

        # -------------------------
        # xG VALIDATION (optional)
        # -------------------------

        hxg = r.get("home_xg","")
        axg = r.get("away_xg","")
        txg = r.get("expected_total_goals","")

        if hxg and axg and txg:
            try:
                hxg = float(hxg)
                axg = float(axg)
                txg = float(txg)

                if abs((hxg + axg) - txg) > 0.25:
                    log(f"WARNING: xG mismatch row {rows_checked} ({hxg}+{axg}!={txg})")

            except:
                log(f"WARNING: invalid xG values row {rows_checked}")

        # -------------------------
        # GAME ID UNIQUENESS
        # -------------------------

        gid = r["game_id"]

        if gid in game_ids:
            log(f"ERROR: Duplicate game_id {gid}")
            errors += 1

        game_ids.add(gid)

# =========================
# FINAL RESULT
# =========================

if errors > 0:
    log(f"FAILED: {errors} errors detected")
    raise ValueError("Validation failed")

log(f"SUCCESS: rows_checked={rows_checked}")
print(f"Validation passed for {MERGE_FILE}")
