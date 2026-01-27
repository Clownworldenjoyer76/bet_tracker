#!/usr/bin/env python3
"""
scripts/nhl_spreads_05.py

Purpose:
- Apply venue-adjusted juice to FAIR puck line odds (underdog +1.5)
- Populates ONLY:
    - puck_line_acceptable_deci
    - puck_line_acceptable_amer

Method:
- Convert fair decimal -> implied probability
- Inflate probability by:
    - 5% if underdog is HOME
    - 6% if underdog is AWAY
- Convert back to odds

No sportsbook lines. No personal edge logic.
"""

import csv
from pathlib import Path
import sys
import math

SPREADS_DIR = Path("docs/win/nhl/spreads")


def deci_to_american(deci: float) -> int:
    if deci >= 2.0:
        return int(round(100 * (deci - 1)))
    else:
        return int(round(-100 / (deci - 1)))


def process_file(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    for row in rows:
        if not row.get("puck_line_fair_deci"):
            continue

        try:
            fair_deci = float(row["puck_line_fair_deci"])
        except ValueError:
            continue

        underdog = row.get("underdog")
        home_team = row.get("home_team")
        away_team = row.get("away_team")

        if not underdog or not home_team or not away_team:
            continue

        # venue-adjusted juice
        if underdog == home_team:
            juice = 0.05
        elif underdog == away_team:
            juice = 0.06
        else:
            continue  # safety: underdog must match one side

        # fair implied probability
        p_fair = 1.0 / fair_deci

        # apply juice on probability
        p_juiced = p_fair * (1.0 + juice)

        # guard against impossible probability
        if p_juiced >= 1.0:
            continue

        acceptable_deci = 1.0 / p_juiced
        acceptable_amer = deci_to_american(acceptable_deci)

        row["puck_line_acceptable_deci"] = f"{acceptable_deci:.6f}"
        row["puck_line_acceptable_amer"] = str(acceptable_amer)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated acceptable puck line odds: {path.name}")


def main():
    files = sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))

    if not files:
        print("No nhl_spreads files found.", file=sys.stderr)
        sys.exit(1)

    for f in files:
        process_file(f)


if __name__ == "__main__":
    main()
