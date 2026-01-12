#!/usr/bin/env python3
"""
Clean Win Probability CSVs — deterministic version

Expected input structure per game:

MM/DD/YYYY
HH:MM AM/PM
Team A (W-L)
Team B (W-L)    Team A win %
Team B win %
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Optional

INPUT_DIR = Path("docs/win")
OUTPUT_DIR = Path("docs/win/clean")

DATE_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")
TIME_RE = re.compile(r"^\s*(\d{1,2}:\d{2}\s*(?:AM|PM))\s*$", re.I)
TEAM_RE = re.compile(r"^\s*(.+?)\s*\(\s*\d+\s*-\s*\d+\s*\)\s*$")
PCT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")

def detect_league(filename: str) -> str:
    for league in ("ncaab", "nba", "nfl", "nhl", "mlb", "wnba", "ncaaf"):
        if league in filename.lower():
            return league
    return "unknown"

def mmddyyyy_to_iso(mm: str, dd: str, yyyy: str) -> str:
    return f"{yyyy}-{mm}-{dd}"

def clean_one_file(path: Path) -> Dict[str, List[Dict[str, str]]]:
    league = detect_league(path.name)
    rows_by_date: Dict[str, List[Dict[str, str]]] = {}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # New game starts ONLY on date
        m = DATE_RE.match(line)
        if not m:
            i += 1
            continue

        date_iso = mmddyyyy_to_iso(m.group(1), m.group(2), m.group(3))
        i += 1

        # Time
        if i >= n or not (tm := TIME_RE.match(lines[i].strip())):
            raise ValueError(f"Missing time after date {date_iso}")
        time_str = tm.group(1).upper()
        i += 1

        # Team A
        if i >= n or not (ta := TEAM_RE.match(lines[i].strip())):
            raise ValueError(f"Missing Team A after {date_iso} {time_str}")
        team_a = ta.group(1).strip()
        i += 1

        # Team B + Team A probability
        if i >= n:
            raise ValueError("Unexpected EOF reading Team B")
        parts = [p for p in lines[i].split("\t") if p.strip()]
        tb = TEAM_RE.match(parts[0].strip())
        if not tb or len(parts) < 2:
            raise ValueError(f"Invalid Team B / prob line: {lines[i]}")
        team_b = tb.group(1).strip()
        prob_a = float(PCT_RE.search(parts[1]).group(1)) / 100.0
        i += 1

        # Team B probability
        if i >= n or not (pb := PCT_RE.search(lines[i])):
            raise ValueError(f"Missing Team B probability after {team_b}")
        prob_b = float(pb.group(1)) / 100.0
        i += 1

        rows = rows_by_date.setdefault(date_iso, [])
        rows.append({
            "date": date_iso,
            "time": time_str,
            "team": team_a,
            "opponent": team_b,
            "win_probability": f"{prob_a:.3f}",
            "league": league,
        })
        rows.append({
            "date": date_iso,
            "time": time_str,
            "team": team_b,
            "opponent": team_a,
            "win_probability": f"{prob_b:.3f}",
            "league": league,
        })

    return rows_by_date

def write_outputs(rows_by_date: Dict[str, List[Dict[str, str]]], league: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for date_iso, rows in rows_by_date.items():
        out_path = OUTPUT_DIR / f"win_prob__clean_{league}_{date_iso}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["date", "time", "team", "opponent", "win_probability", "league"],
            )
            writer.writeheader()
            writer.writerows(rows)

        print(f"Wrote {out_path} ({len(rows)} rows)")

def main():
    files = sorted(INPUT_DIR.glob("win_prob_*.csv"))
    if not files:
        print("No input files found")
        return

    for path in files:
        league = detect_league(path.name)
        rows_by_date = clean_one_file(path)
        write_outputs(rows_by_date, league)

if __name__ == "__main__":
    main()
