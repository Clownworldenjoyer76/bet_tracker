# scripts/dk_02.py

#!/usr/bin/env python3

import csv
from pathlib import Path

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/cleaned")

ERROR_DIR = Path("docs/win/errors/02_dk_prep")
ERROR_LOG = ERROR_DIR / "dk_02_game_id.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def log(msg: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# =========================
# CORE
# =========================

def process_file(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "game_id" not in fieldnames:
        fieldnames.append("game_id")

    for row in rows:
        # Identity is NOT knowable at row level for DK data.
        # It is assigned safely at game-group level in dk_03.py.
        row["game_id"] = ""

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log(f"{path.name} | rows={len(rows)} | game_id deferred")

# =========================
# MAIN
# =========================

def main():
    log("DK_02 START (identity deferred to dk_03)")

    for path in INPUT_DIR.glob("dk_*_*.csv"):
        process_file(path)

    log("DK_02 END\n")

if __name__ == "__main__":
    main()
