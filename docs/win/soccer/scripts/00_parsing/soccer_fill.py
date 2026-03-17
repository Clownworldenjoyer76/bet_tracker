#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/soccer_fill.py

import csv
from pathlib import Path
from datetime import datetime
import re

# =========================
# PATHS
# =========================

TOTALS_DIR = Path("docs/win/soccer/00_intake/sportsbook/totals_odds")
COMBINED_DIR = Path("docs/win/soccer/00_intake/sportsbook/combined")

ERROR_DIR = Path("docs/win/soccer/errors/00_parsing")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "soccer_fill.txt"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# HELPERS
# =========================

def normalize(text):
    if not text:
        return ""
    text = text.lower().replace("&", "and")
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text

def load_totals(file_path):
    data = {}

    if not file_path.exists():
        return data

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            key = (
                row.get("match_date"),
                normalize(row.get("home_team")),
                normalize(row.get("away_team")),
            )

            data[key] = {
                "dk_over25_american": row.get("over25_american", ""),
                "dk_under25_american": row.get("under25_american", ""),
                "dk_over35_american": row.get("over35_american", ""),
                "dk_under35_american": row.get("under35_american", ""),
            }

    return data

# =========================
# PROCESS FILES
# =========================

combined_files = list(COMBINED_DIR.glob("soccer_*.csv"))

for combined_file in combined_files:

    date = combined_file.stem.replace("soccer_", "")

    # Build totals file map
    totals_files = {
        "epl": TOTALS_DIR / f"soccer_{date}_EPL_totals.csv",
        "laliga": TOTALS_DIR / f"soccer_{date}_La_Liga_totals.csv",
        "seriea": TOTALS_DIR / f"soccer_{date}_Serie_A_totals.csv",
        "bundesliga": TOTALS_DIR / f"soccer_{date}_Bundesliga_totals.csv",
        "ligue1": TOTALS_DIR / f"soccer_{date}_Ligue_1_totals.csv",
        "mls": TOTALS_DIR / f"soccer_{date}_MLS_totals.csv",
    }

    # Load all totals into one dict
    totals_data = {}

    for market, path in totals_files.items():
        market_data = load_totals(path)
        totals_data.update(market_data)

    updated_rows = []
    fieldnames = []

    with open(combined_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Add new columns if not present
        for col in [
            "dk_over25_american",
            "dk_under25_american",
            "dk_over35_american",
            "dk_under35_american",
        ]:
            if col not in fieldnames:
                fieldnames.append(col)

        for row in reader:

            key = (
                row.get("match_date"),
                normalize(row.get("home_team")),
                normalize(row.get("away_team")),
            )

            totals = totals_data.get(key, {})

            row["dk_over25_american"] = totals.get("dk_over25_american", "")
            row["dk_under25_american"] = totals.get("dk_under25_american", "")
            row["dk_over35_american"] = totals.get("dk_over35_american", "")
            row["dk_under35_american"] = totals.get("dk_under35_american", "")

            updated_rows.append(row)

    # Write back (atomic)
    temp_file = combined_file.with_suffix(".tmp")

    with open(temp_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    temp_file.replace(combined_file)

    print(f"Updated {combined_file}")

log("soccer_fill complete")
