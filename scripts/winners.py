#!/usr/bin/env python3

import csv
from pathlib import Path
from datetime import datetime

FINAL_DIR = Path("docs/win/final")
MANUAL_DIR = Path("docs/win/manual/normalized")
OUT_DIR = FINAL_DIR / "winners"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(value):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except Exception:
            pass
    return None


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    manual_rows = []
    for p in MANUAL_DIR.glob("*.csv"):
        manual_rows.extend(load_csv(p))

    winners_by_date = {}

    for final_path in FINAL_DIR.glob("*.csv"):
        final_rows = load_csv(final_path)
        if not final_rows:
            continue

        for f in final_rows:
            f_date = parse_date(f["date"])
            if not f_date:
                continue

            for m in manual_rows:
                # STRICT MATCH: date, team, opponent, league
                m_date = parse_date(m.get("date", ""))
                if (
                    m_date == f_date
                    and f["team"].strip() == m["team"].strip()
                    and f["opponent"].strip() == m["opponent"].strip()
                    and f["league"].strip() == m["league"].strip()
                ):
                    try:
                        acceptable = float(f["personally_acceptable_american_odds"])
                        actual = float(m["odds"])
                    except Exception:
                        continue

                    # ONLY RULE
                    if actual >= acceptable:
                        winners_by_date.setdefault(f_date, []).append(
                            {
                                "Date": f["date"],
                                "Time": f["time"],
                                "Team": f["team"],
                                "Opponent": f["opponent"],
                                "win_probability": f["win_probability"],
                                "league": f["league"],
                                "personally_acceptable_american_odds": acceptable,
                                "Odds": actual,
                            }
                        )

    for d, rows in winners_by_date.items():
        out = OUT_DIR / f"winners_{d.year}_{d.day:02d}_{d.month:02d}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
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
