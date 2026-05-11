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
) -> dict | None:
    files = sorted(folder.glob(pattern)) if folder.exists() else []

    future_files = []
    for path in files:
        d = leading_file_date(path)
        if d and d > TODAY:
            future_files.append(path)

    if len(future_files) <= 1:
        return {
            "league": league,
            "folder": str(folder),
            "future_count": len(future_files),
            "latest_file": latest_file_name(future_files if future_files else files),
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

    alerts_to_check = [
        {
            "league": "ufc_predictions",
            "folder": UFC_PRED_DIR,
            "pattern": "*_ufc_predictions.csv",
        },
        {
            "league": "ufc_sportsbook",
            "folder": UFC_BOOK_DIR,
            "pattern": "*_ufc_odds.csv",
        },
    ]

    for item in alerts_to_check:
        alert = check_folder(
            league=item["league"],
            folder=item["folder"],
            pattern=item["pattern"],
        )
        if alert:
            alerts.append(alert)

    if SOCCER_PRED_BASE.exists():
        for league_dir in sorted(SOCCER_PRED_BASE.iterdir()):
            if not league_dir.is_dir():
                continue

            league = league_dir.name

            alert = check_folder(
                league=league,
                folder=league_dir,
                pattern=f"*_{league}.csv",
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
