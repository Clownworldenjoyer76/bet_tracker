#!/usr/bin/env python3

import csv
from pathlib import Path
from datetime import datetime

FINAL_DIR = Path("docs/win/final")
MANUAL_DIR = Path("docs/win/manual/normalized")
OUT_DIR = FINAL_DIR / "winners"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key_no_date(row):
    return (
        row["team"].strip(),
        row["opponent"].strip(),
        row["league"].strip(),
    )


def main():
    # Load manual normalized rows into lookup (NO DATE IN KEY)
    manual_lookup = {}
    for path in MANUAL_DIR.glob("*.csv"):
        for row in load_csv(path):
            manual_lookup[key_no_date(row)] = row

    winners_by_date = {}

    for final_path in FINAL_DIR.glob("*.csv"):
        final_rows = load_csv(final_path)
        if not final_rows:
            continue

        for frow in final_rows:
            key = key_no_date(frow)
            if key not in manual_lookup:
                continue

            mrow = manual_lookup[key]

            f_date = parse_date(frow["date"])
            if not f_date:
                continue

            try:
                final_odds = float(frow["odds"])
                acceptable_odds = float(
                    mrow["personally_acceptable_american_odds"]
                )
            except (KeyError, ValueError):
                continue

            # CORRECT AMERICAN ODDS COMPARISON
            # More positive = better price
            if final_odds < acceptable_odds:
                winners_by_date.setdefault(f_date, []).append(
                    {
                        "Date": frow["date"],
                        "Time": frow["time"],
                        "Team": frow["team"],
                        "Opponent": frow["opponent"],
                        "win_probability": frow["win_probability"],
                        "league": frow["league"],
                        "personally_acceptable_american_odds": acceptable_odds,
                        "Odds": final_odds,
                    }
                )

    for d, rows in winners_by_date.items():
        out_path = OUT_DIR / f"winners_{d.year}_{d.day:02d}_{d.month:02d}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "Date",
                    "Time",
                    "Team",
                    "Opponent",
                    "win_probability",
                    "league",
                    "personally_acceptable_american_odds",
                    "Odds",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
