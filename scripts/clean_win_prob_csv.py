#!/usr/bin/env python3
"""
Clean Win Probability CSVs

Parses frontend-scraped, line-oriented exports in docs/win/win_prob_*.csv.

Time handling (IMPORTANT):
- Scraped times are assumed to be US/Pacific
- All output times are normalized to US/Eastern
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo


INPUT_DIR = Path("docs/win")
OUTPUT_DIR = Path("docs/win/clean")

PACIFIC = ZoneInfo("America/Los_Angeles")
EASTERN = ZoneInfo("America/New_York")

DATE_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")
TIME_RE = re.compile(r"^\s*(\d{1,2}:\d{2})\s*(AM|PM)\s*$", re.IGNORECASE)
PCT_RE = re.compile(r"^\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*$")
TEAM_RE = re.compile(r"^\s*(.+?)\s*\(\s*\d+\s*-\s*\d+\s*\)\s*$")


def detect_league(filename: str) -> str:
    name = filename.lower()
    for league in ("ncaab", "nba", "nfl", "nhl", "mlb", "wnba", "ncaaf"):
        if league in name:
            return league
    return "unknown"


def mmddyyyy_to_iso(mm: str, dd: str, yyyy: str) -> str:
    return f"{yyyy}-{mm}-{dd}"


def convert_pt_to_et(date_iso: str, time_str: str) -> str:
    """
    date_iso: YYYY-MM-DD
    time_str: HH:MM AM/PM  (scraped, Pacific)
    returns: HH:MM AM/PM   (Eastern)
    """
    dt = datetime.strptime(f"{date_iso} {time_str}", "%Y-%m-%d %I:%M %p")
    dt = dt.replace(tzinfo=PACIFIC)
    dt_et = dt.astimezone(EASTERN)
    return dt_et.strftime("%I:%M %p").lstrip("0")


def strip_team_record(team_line: str) -> Optional[str]:
    m = TEAM_RE.match(team_line.strip())
    if not m:
        return None
    return m.group(1).strip()


def parse_pct_token(token: str) -> Optional[float]:
    m = PCT_RE.match(token.strip())
    if not m:
        return None
    pct_val = float(m.group(1))
    return max(0.0, min(1.0, pct_val / 100.0))


def parse_team_and_optional_pct(raw_line: str) -> Tuple[Optional[str], Optional[float]]:
    parts = [p.strip() for p in raw_line.split("\t") if p.strip()]
    if not parts:
        return None, None

    team = strip_team_record(parts[0])
    if team is None:
        return None, None

    pct = parse_pct_token(parts[1]) if len(parts) >= 2 else None
    return team, pct


def parse_pct_line(raw_line: str) -> Optional[float]:
    tokens = [t.strip() for t in raw_line.split("\t") if t.strip()]
    if not tokens:
        return None
    return parse_pct_token(tokens[0])


def is_junk_header_line(line: str) -> bool:
    s = line.strip().lower()
    if not s:
        return True

    header_phrases = (
        "time", "teams", "win", "best", "spread",
        "points", "total", "o/u", "bet", "value",
        "more details", "ml",
    )

    if any(p in s for p in header_phrases):
        if DATE_RE.match(line) or TIME_RE.match(line) or strip_team_record(line):
            return False
        return True

    return False


def clean_one_file(path: Path) -> Dict[str, List[Dict[str, str]]]:
    league = detect_league(path.name)
    out_by_date: Dict[str, List[Dict[str, str]]] = {}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    current_date: Optional[str] = None
    current_time_raw: Optional[str] = None

    team_a = team_b = None
    prob_a = prob_b = None

    def flush():
        nonlocal team_a, team_b, prob_a, prob_b
        if not (current_date and current_time_raw and team_a and team_b):
            return

        if prob_a is None and prob_b is not None:
            prob_a = 1.0 - prob_b
        if prob_b is None and prob_a is not None:
            prob_b = 1.0 - prob_a
        if prob_a is None or prob_b is None:
            team_a = team_b = prob_a = prob_b = None
            return

        time_et = convert_pt_to_et(current_date, current_time_raw)

        rows = out_by_date.setdefault(current_date, [])
        rows.append({
            "date": current_date,
            "time": time_et,
            "team": team_a,
            "opponent": team_b,
            "win_probability": f"{prob_a:.3f}",
            "league": league,
        })
        rows.append({
            "date": current_date,
            "time": time_et,
            "team": team_b,
            "opponent": team_a,
            "win_probability": f"{prob_b:.3f}",
            "league": league,
        })

        team_a = team_b = prob_a = prob_b = None

    for raw in lines:
        if is_junk_header_line(raw):
            continue

        if m := DATE_RE.match(raw):
            flush()
            current_date = mmddyyyy_to_iso(m.group(1), m.group(2), m.group(3))
            current_time_raw = None
            continue

        if m := TIME_RE.match(raw):
            flush()
            current_time_raw = f"{m.group(1)} {m.group(2).upper()}"
            continue

        if current_date and current_time_raw:
            team, pct = parse_team_and_optional_pct(raw)
            if team:
                if team_a is None:
                    team_a = team
                    if pct is not None:
                        prob_a = pct
                elif team_b is None:
                    team_b = team
                    if pct is not None and prob_a is None:
                        prob_a = pct
                else:
                    flush()
                    team_a = team
                    prob_a = pct
                continue

            pct_only = parse_pct_line(raw)
            if pct_only is not None:
                if prob_a is None:
                    prob_a = pct_only
                elif prob_b is None:
                    prob_b = pct_only
                flush()
                continue

    flush()
    return out_by_date


def write_outputs(rows_by_date: Dict[str, List[Dict[str, str]]], league: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for iso_date, rows in rows_by_date.items():
        if not rows:
            continue

        out_path = OUTPUT_DIR / f"win_prob__clean_{league}_{iso_date}.csv"
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
        if rows_by_date:
            write_outputs(rows_by_date, league)
        else:
            print(f"No games parsed from {path.name}")


if __name__ == "__main__":
    main()
