#!/usr/bin/env python3
# scripts/email_alert_future_files.py
"""
Future-date file count alerts.

Creates alert_body.txt only when at least one configured folder has
1 or fewer future-dated files.

Checks:

1. docs/win/mma/ufc/00_intake/predictions/{date}_ufc_predictions.csv
2. docs/win/mma/ufc/00_intake/sportsbook/{date}_ufc_odds.csv
3. docs/win/soccer/00_intake/predictions/{league}/{date}_{league}.csv
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ALERT_FILE = Path("alert_body.txt")
TODAY = datetime.now(ZoneInfo("America/New_York")).date()

UFC_PRED_DIR = Path("docs/win/mma/ufc/00_intake/predictions")
UFC_BOOK_DIR = Path("docs/win/mma/ufc/00_intake/sportsbook")
SOCCER_PRED_BASE = Path("docs/win/soccer/00_intake/predictions")


def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y_%m_%d").date()
    except ValueError:
        return None


def latest_file_name(files: list[Path]) -> str:
    if not files:
        return "NONE"

    dated = []
    for path in files:
        m = re.search(r"(\d{4}_\d{2}_\d{2})", path.name)
        if not m:
            continue

        d = parse_date(m.group(1))
        if d:
            dated.append((d, path.name))

    if dated:
        dated.sort(key=lambda x: x[0])
        return dated[-1][1]

    return sorted(p.name for p in files)[-1]


def check_folder(
    league: str,
    folder: Path,
    pattern: str,
    date_regex: str,
) -> dict | None:
    files = sorted(folder.glob(pattern)) if folder.exists() else []

    future_files = []
    date_re = re.compile(date_regex)

    for path in files:
        m = date_re.search(path.name)
        if not m:
            continue

        d = parse_date(m.group(1))
        if d and d > TODAY:
            future_files.append(path)

    if len(future_files) <= 1:
        latest = latest_file_name(future_files if future_files else files)

        return {
            "league": league,
            "folder": str(folder),
            "future_count": len(future_files),
            "latest_file": latest,
        }

    return None


def build_alert_block(alert: dict) -> str:
    return "\n".join([
        "Future File Count Alert",
        "",
        f"League: {alert['league']}",
        f"Folder: {alert['folder']}",
        f"Future files found: {alert['future_count']}",
        f"Latest file: {alert['latest_file']}",
        "Threshold: expected more than 1 future-dated file",
    ])


def main() -> int:
    if ALERT_FILE.exists():
        ALERT_FILE.unlink()

    alerts = []

    # UFC predictions
    alert = check_folder(
        league="ufc_predictions",
        folder=UFC_PRED_DIR,
        pattern="*_ufc_predictions.csv",
        date_regex=r"(\d{4}_\d{2}_\d{2})_ufc_predictions\.csv$",
    )
    if alert:
        alerts.append(alert)

    # UFC sportsbook odds
    alert = check_folder(
        league="ufc_sportsbook",
        folder=UFC_BOOK_DIR,
        pattern="*_ufc_odds.csv",
        date_regex=r"(\d{4}_\d{2}_\d{2})_ufc_odds\.csv$",
    )
    if alert:
        alerts.append(alert)

    # Soccer predictions by league folder
    if SOCCER_PRED_BASE.exists():
        for league_dir in sorted(SOCCER_PRED_BASE.iterdir()):
            if not league_dir.is_dir():
                continue

            league = league_dir.name

            alert = check_folder(
                league=league,
                folder=league_dir,
                pattern=f"*_{league}.csv",
                date_regex=rf"(\d{{4}}_\d{{2}}_\d{{2}})_{re.escape(league)}\.csv$",
            )
            if alert:
                alerts.append(alert)
    else:
        alerts.append({
            "league": "soccer_predictions",
            "folder": str(SOCCER_PRED_BASE),
            "future_count": 0,
            "latest_file": "NONE",
        })

    if alerts:
        body = [
            "Betting repo data alert triggered.",
            "",
            f"Run date: {TODAY.isoformat()} America/New_York",
            "",
        ]

        for i, alert in enumerate(alerts, start=1):
            if i > 1:
                body.append("")
                body.append("-" * 60)
                body.append("")
            body.append(build_alert_block(alert))

        ALERT_FILE.write_text("\n".join(body) + "\n", encoding="utf-8")

        print(f"ALERTS FOUND: {len(alerts)}")
        print(f"WROTE {ALERT_FILE}")
    else:
        print("No alerts triggered.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
