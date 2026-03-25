# docs/win/hockey/scripts/01_merge/merge_intake.py

#!/usr/bin/env python3

import sys
import csv
from pathlib import Path
from datetime import datetime, UTC

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
        f.write(f"{datetime.now(UTC).isoformat()} | {msg}\n")

# =========================
# HELPERS
# =========================

def load_raw(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def to_float(x):
    try:
        return float(x)
    except Exception:
        return None

key_fields = ["game_date", "home_team", "away_team"]

# =========================
# FIELDNAMES
# =========================

FIELDNAMES = [
    "league", "market", "game_date", "game_time",
    "home_team", "away_team", "game_id",
    "home_prob", "away_prob",
    "away_projected_goals", "home_projected_goals", "total_projected_goals",
    "away_puck_line", "home_puck_line", "total",
    "away_dk_puck_line_american", "home_dk_puck_line_american",
    "dk_total_over_american", "dk_total_under_american",
    "away_dk_moneyline_american", "home_dk_moneyline_american",
]

# =========================
# PROCESS
# =========================

prediction_files = list(PRED_DIR.glob("hockey_*.csv"))

for pred_file in prediction_files:

    slate_date = pred_file.stem.replace("hockey_", "")

    PRED_FILE = PRED_DIR / f"hockey_{slate_date}.csv"
    BOOK_FILE = SPORTSBOOK_DIR / f"hockey_{slate_date}.csv"
    OUTFILE = MERGE_DIR / f"hockey_NHL_{slate_date}.csv"

    if not PRED_FILE.exists() or not BOOK_FILE.exists():
        log(f"MISSING FILE: {slate_date}")
        continue

    pred_rows = load_raw(PRED_FILE)
    book_rows = load_raw(BOOK_FILE)

    pred_map = {tuple(r[k] for k in key_fields): r for r in pred_rows}
    book_map = {tuple(r[k] for k in key_fields): r for r in book_rows}

    merged = []
    dropped = 0

    # =========================
    # MERGE
    # =========================

    for key, p in pred_map.items():

        if key not in book_map:
            log(f"MISSING MATCH: {p['home_team']} vs {p['away_team']}")
            dropped += 1
            continue

        b = book_map[key]

        # Type enforcement
        home_prob = to_float(p.get("home_prob"))
        away_prob = to_float(p.get("away_prob"))

        if home_prob is None or away_prob is None:
            log(f"TYPE ISSUE: {p['home_team']} vs {p['away_team']} — prob is None; dropping row")
            dropped += 1
            continue

        # Validate that home_prob + away_prob ≈ 1.0.
        prob_sum = home_prob + away_prob
        if abs(prob_sum - 1.0) > 0.01:
            log(
                f"PROB SUM WARNING: {p['home_team']} vs {p['away_team']} "
                f"home_prob={home_prob} away_prob={away_prob} sum={prob_sum:.4f} — dropping row"
            )
            dropped += 1
            continue

        home_pl = to_float(b.get("home_puck_line"))
        away_pl = to_float(b.get("away_puck_line"))

        if home_pl is not None and away_pl is not None:
            if round(home_pl + away_pl, 6) != 0:
                log(
                    f"PUCK LINE IMBALANCE: {p['home_team']} vs {p['away_team']} "
                    f"home={home_pl} away={away_pl} — dropping row"
                )
                dropped += 1
                continue

        # FIX #4: Replace spaces in team names within game_id with underscores
        # so it is safe to use as a join key in downstream CSVs and as a filename
        # component. Display fields (home_team, away_team) are unchanged.
        away_slug = p["away_team"].strip().replace(" ", "_")
        home_slug = p["home_team"].strip().replace(" ", "_")
        game_id = f"{p['game_date']}_{away_slug}_{home_slug}"

        merged.append({
            "league": p.get("league"),
            "market": p.get("market"),
            "game_date": p.get("game_date"),
            "game_time": b.get("game_time"),
            "home_team": p.get("home_team"),
            "away_team": p.get("away_team"),
            "game_id": game_id,
            "home_prob": home_prob,
            "away_prob": away_prob,
            "away_projected_goals": to_float(p.get("away_projected_goals")),
            "home_projected_goals": to_float(p.get("home_projected_goals")),
            "total_projected_goals": to_float(p.get("total_projected_goals")),
            "away_puck_line": away_pl,
            "home_puck_line": home_pl,
            "total": to_float(b.get("total")),
            "away_dk_puck_line_american": to_float(b.get("away_dk_puck_line_american")),
            "home_dk_puck_line_american": to_float(b.get("home_dk_puck_line_american")),
            "dk_total_over_american": to_float(b.get("dk_total_over_american")),
            "dk_total_under_american": to_float(b.get("dk_total_under_american")),
            "away_dk_moneyline_american": to_float(b.get("away_dk_moneyline_american")),
            "home_dk_moneyline_american": to_float(b.get("home_dk_moneyline_american")),
        })

    # =========================
    # ORPHAN SPORTSBOOK ROWS
    # =========================

    for key, b in book_map.items():
        if key not in pred_map:
            log(f"ORPHAN SPORTSBOOK ROW: {b['home_team']} vs {b['away_team']}")

    # =========================
    # SUMMARY
    # =========================

    log(
        f"SUMMARY: slate={slate_date} pred={len(pred_map)} book={len(book_map)} "
        f"merged={len(merged)} dropped={dropped}"
    )

    if not merged:
        continue

    with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(merged)

    print(f"Wrote {OUTFILE}")
