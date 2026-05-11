#!/usr/bin/env python3
# scripts/email_alert_future_files.py

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


def leading_file_date(path: Path):
    """
    Extract date only from the START of the filename.

    Examples:
      2026_06_10_BUNDESLIGA.csv -> 2026-06-10
      2026_05_09_ufc_predictions.csv -> 2026-05-09
      2026_05_09_ufc_odds.csv -> 2026-05-09
    """
    m = re.match(r"^(\d{4}_\d{2}_\d{2})_", path.name)
    if not m:
        return None
    return parse_date(m.group(1))


def latest_file_name(files: list[Path]) -> str:
    if not files:
        return "NONE"

    dated = []
    for path in files:
        d = leading_file_date(path)
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
    alert_when_future_count_lte: int,
) -> dict | None:
    files = sorted(folder.glob(pattern)) if folder.exists() else []

    future_files = []
    for path in files:
        d = leading_file_date(path)
        if d and d > TODAY:
            future_files.append(path)

    if len(future_files) <= alert_when_future_count_lte:
        return {
            "league": league,
            "folder": str(folder),
            "future_count": len(future_files),
            "latest_file": latest_file_name(future_files if future_files else files),
            "threshold": alert_when_future_count_lte,
        }

    return None


def threshold_text(alert: dict) -> str:
    threshold = alert["threshold"]

    if threshold == 0:
        return "Threshold: expected at least 1 future-dated file"

    if threshold == 1:
        return "Threshold: expected more than 1 future-dated file"

    return f"Threshold: expected more than {threshold} future-dated files"


def build_alert_block(alert: dict) -> str:
    return "\n".join([
        "Future File Count Alert",
        "",
        f"League: {alert['league']}",
        f"Folder: {alert['folder']}",
        f"Future files found: {alert['future_count']}",
        f"Latest file: {alert['latest_file']}",
        threshold_text(alert),
    ])


def main() -> int:
    if ALERT_FILE.exists():
        ALERT_FILE.unlink()

    alerts = []

    # UFC predictions:
    # Alert only when there are 0 upcoming/future files.
    alert = check_folder(
        league="ufc_predictions",
        folder=UFC_PRED_DIR,
        pattern="*_ufc_predictions.csv",
        alert_when_future_count_lte=0,
    )
    if alert:
        alerts.append(alert)

    # UFC sportsbook:
    # Alert only when there are 0 upcoming/future files.
    alert = check_folder(
        league="ufc_sportsbook",
        folder=UFC_BOOK_DIR,
        pattern="*_ufc_odds.csv",
        alert_when_future_count_lte=0,
    )
    if alert:
        alerts.append(alert)

    # Soccer prediction folders:
    # Alert when there are 1 or fewer upcoming/future files.
    # Scan all CSVs in each folder because folders like "normalized" may contain
    # multiple league file names.
    if SOCCER_PRED_BASE.exists():
        for league_dir in sorted(SOCCER_PRED_BASE.iterdir()):
            if not league_dir.is_dir():
                continue

            folder_name = league_dir.name

            alert = check_folder(
                league=folder_name,
                folder=league_dir,
                pattern="*.csv",
                alert_when_future_count_lte=1,
            )
            if alert:
                alerts.append(alert)
    else:
        alerts.append({
            "league": "soccer_predictions",
            "folder": str(SOCCER_PRED_BASE),
            "future_count": 0,
            "latest_file": "NONE",
            "threshold": 1,
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
