#!/usr/bin/env python3
# scripts/email_alert_win_pct.py

from __future__ import annotations

import csv
from pathlib import Path


ALERT_FILE = Path("alert_body.txt")

FILES_TO_CHECK = [
    {
        "league": "bundesliga",
        "path": Path("docs/win/soccer/05_final_scores/bundesliga_market_tally.csv"),
        "threshold": 0.60,
    },
    {
        "league": "epl",
        "path": Path("docs/win/soccer/05_final_scores/epl_market_tally.csv"),
        "threshold": 0.60,
    },
    {
        "league": "laliga",
        "path": Path("docs/win/soccer/05_final_scores/laliga_market_tally.csv"),
        "threshold": 0.60,
    },
    {
        "league": "ligue1",
        "path": Path("docs/win/soccer/05_final_scores/ligue1_market_tally.csv"),
        "threshold": 0.60,
    },
    {
        "league": "seriea",
        "path": Path("docs/win/soccer/05_final_scores/seriea_market_tally.csv"),
        "threshold": 0.60,
    },
    {
        "league": "mls",
        "path": Path("docs/win/soccer/05_final_scores/mls_market_tally.csv"),
        "threshold": 0.60,
    },
    {
        "league": "all_soccer",
        "path": Path("docs/win/soccer/05_final_scores/all_soccer_market_tally.csv"),
        "threshold": 0.60,
    },
    {
        "league": "mlb",
        "path": Path("docs/win/baseball/05_final_scores/mlb_summary_overall.csv"),
        "threshold": 0.60,
    },
    {
        "league": "nba",
        "path": Path("docs/win/basketball/05_final_scores/nba_summary_overall.csv"),
        "threshold": 0.60,
    },
    {
        "league": "ncaam",
        "path": Path("docs/win/basketball/05_final_scores/ncaam_summary_overall.csv"),
        "threshold": 0.60,
    },
    {
        "league": "wnba",
        "path": Path("docs/win/basketball/05_final_scores/wnba_summary_overall.csv"),
        "threshold": 0.60,
    },
    {
        "league": "nhl",
        "path": Path("docs/win/final_scores/nhl_market_tally.csv"),
        "threshold": 0.70,
    },
    {
        "league": "ufc",
        "path": Path("docs/win/mma/ufc/04_final/ufc_summary_overall.csv"),
        "threshold": 0.70,
    },
]


def safe_float(value):
    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    try:
        return float(s)
    except ValueError:
        return None


def get_case_insensitive(row: dict, *names: str):
    lowered = {str(k).lower(): v for k, v in row.items()}

    for name in names:
        v = lowered.get(name.lower())
        if v is not None:
            return v

    return None


def read_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_alert_block(alert: dict) -> str:
    lines = [
        "Win Percent Alert",
        "",
        f"League: {alert['league']}",
        f"Folder: {alert['folder']}",
        f"File: {alert['file']}",
        f"Issue: {alert['issue']}",
    ]

    if alert.get("details"):
        lines.extend(["", alert["details"]])

    return "\n".join(lines)


def check_file(item: dict) -> list[dict]:
    league = item["league"]
    path = item["path"]
    threshold = item["threshold"]

    alerts = []

    if not path.exists():
        alerts.append({
            "league": league,
            "folder": str(path.parent),
            "file": path.name,
            "issue": "File missing",
            "details": "",
        })
        return alerts

    rows = read_csv_rows(path)

    for i, row in enumerate(rows, start=1):
        total_raw = get_case_insensitive(row, "total", "Total")
        win_pct_raw = get_case_insensitive(row, "Win_Pct", "win_pct")

        total = safe_float(total_raw)
        win_pct = safe_float(win_pct_raw)

        if total is None or win_pct is None:
            continue

        if total >= 4 and win_pct < threshold:
            market_type = get_case_insensitive(row, "market_type", "Market_Type") or ""
            bucket_dimension = get_case_insensitive(row, "bucket_dimension", "Bucket_Dimension") or ""
            bucket = get_case_insensitive(row, "bucket", "Bucket") or ""

            detail_parts = [
                f"Row: {i}",
                f"Total: {total:g}",
                f"Win_Pct: {win_pct:.4f}",
                f"Threshold: {threshold:.2f}",
            ]

            if market_type:
                detail_parts.append(f"Market: {market_type}")
            if bucket_dimension:
                detail_parts.append(f"Bucket Dimension: {bucket_dimension}")
            if bucket:
                detail_parts.append(f"Bucket: {bucket}")

            alerts.append({
                "league": league,
                "folder": str(path.parent),
                "file": path.name,
                "issue": "Win Percent below threshold",
                "details": "\n".join(detail_parts),
            })

    return alerts


def main() -> int:
    if ALERT_FILE.exists():
        ALERT_FILE.unlink()

    alerts = []

    for item in FILES_TO_CHECK:
        alerts.extend(check_file(item))

    if alerts:
        body = [
            "Betting repo data alert triggered.",
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
