#!/usr/bin/env python3
"""
Clean Win Probability CSVs

This script is built to parse the *actual* frontend-scraped export format observed in
docs/win/win_prob_*.csv (line-oriented, not a real rectangular CSV).

Key rule (per your correction):
- The FIRST win probability shown for a matchup belongs to the FIRST team listed.
  In the observed file, that first probability often appears on the SAME LINE as the
  SECOND team name (because of how the web page scrape lays out the table).

Observed pattern (common):
    MM/DD/YYYY
    HH:MM AM
    Team A (record)
    Team B (record) <TAB> Pct_for_Team_A
    Pct_for_Team_B <TAB>
    ... odds/markets noise ...
    (next matchup)

Output:
- Writes cleaned files to: docs/win/clean/win_prob__clean_{league}_{YYYY-MM-DD}.csv
- Columns: date,time,team,opponent,win_probability,league
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


INPUT_DIR = Path("docs/win")
OUTPUT_DIR = Path("docs/win/clean")

DATE_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")
TIME_RE = re.compile(r"^\s*(\d{1,2}:\d{2})\s*(AM|PM)\s*$", re.IGNORECASE)
PCT_RE = re.compile(r"^\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*$")
TEAM_RE = re.compile(r"^\s*(.+?)\s*\(\s*\d+\s*-\s*\d+\s*\)\s*$")  # "Team Name (12-3)"


def detect_league(filename: str) -> str:
    name = filename.lower()
    for league in ("ncaab", "nba", "nfl", "nhl", "mlb", "wnba", "ncaaf"):
        if league in name:
            return league
    return "unknown"


def mmddyyyy_to_iso(mm: str, dd: str, yyyy: str) -> str:
    return f"{yyyy}-{mm}-{dd}"


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
    """
    Team lines sometimes appear as: 'Team Name (12-3)\\t56.2%'
    Returns (team_name, pct_decimal_if_present)
    """
    parts = [p.strip() for p in raw_line.split("\t") if p.strip() != ""]
    if not parts:
        return None, None

    team = strip_team_record(parts[0])
    if team is None:
        return None, None

    pct = None
    if len(parts) >= 2:
        pct = parse_pct_token(parts[1])

    return team, pct


def parse_pct_line(raw_line: str) -> Optional[float]:
    """
    Handles lines like '43.8%' or '43.8%\\t' or '43.8'.
    """
    s = raw_line.strip()
    if not s:
        return None

    tokens = [t.strip() for t in s.split("\t") if t.strip() != ""]
    if not tokens:
        return None

    return parse_pct_token(tokens[0])


def is_junk_header_line(line: str) -> bool:
    s = line.strip().lower()
    if not s:
        return True

    header_phrases = (
        "time",
        "teams",
        "win",
        "best",
        "spread",
        "points",
        "total",
        "o/u",
        "bet",
        "value",
        "more details",
        "ml",
    )

    # If it looks like the header block and it's NOT a date/time/team line, treat as junk
    if any(p in s for p in header_phrases):
        if DATE_RE.match(line) or TIME_RE.match(line) or strip_team_record(line):
            return False
        return True

    return False


def clean_one_file(path: Path) -> Dict[str, List[Dict[str, str]]]:
    """
    Returns dict: iso_date -> list of output rows for that date.
    """
    league = detect_league(path.name)
    out_by_date: Dict[str, List[Dict[str, str]]] = {}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    current_date: Optional[str] = None
    current_time: Optional[str] = None

    team_a: Optional[str] = None
    team_b: Optional[str] = None
    prob_a: Optional[float] = None
    prob_b: Optional[float] = None

    def flush_match_if_ready():
        nonlocal team_a, team_b, prob_a, prob_b, current_date, current_time
        if not (current_date and current_time and team_a and team_b):
            return

        # If one prob is missing, infer complement
        if prob_a is None and prob_b is not None:
            prob_a = max(0.0, min(1.0, 1.0 - prob_b))
        if prob_b is None and prob_a is not None:
            prob_b = max(0.0, min(1.0, 1.0 - prob_a))

        # If still missing, drop the block (do not crash)
        if prob_a is None or prob_b is None:
            team_a = team_b = None
            prob_a = prob_b = None
            return

        rows = out_by_date.setdefault(current_date, [])
        rows.append(
            {
                "date": current_date,
                "time": current_time,
                "team": team_a,
                "opponent": team_b,
                "win_probability": f"{prob_a:.3f}",
                "league": league,
            }
        )
        rows.append(
            {
                "date": current_date,
                "time": current_time,
                "team": team_b,
                "opponent": team_a,
                "win_probability": f"{prob_b:.3f}",
                "league": league,
            }
        )

        team_a = team_b = None
        prob_a = prob_b = None

    i = 0
    while i < len(lines):
        raw = lines[i]

        if is_junk_header_line(raw):
            i += 1
            continue

        dm = DATE_RE.match(raw)
        if dm:
            flush_match_if_ready()
            current_date = mmddyyyy_to_iso(dm.group(1), dm.group(2), dm.group(3))
            current_time = None
            team_a = team_b = None
            prob_a = prob_b = None
            i += 1
            continue

        tm = TIME_RE.match(raw)
        if tm:
            flush_match_if_ready()
            # Normalize to "HH:MM AM/PM"
            current_time = f"{tm.group(1)} {tm.group(2).upper()}"
            team_a = team_b = None
            prob_a = prob_b = None
            i += 1
            continue

        if current_date and current_time:
            # Team line?
            team, pct_on_line = parse_team_and_optional_pct(raw)
            if team is not None:
                if team_a is None:
                    team_a = team
                    # If a pct is ever present here, it belongs to team_a (first team listed)
                    if pct_on_line is not None:
                        prob_a = pct_on_line
                elif team_b is None:
                    team_b = team
                    # CRITICAL RULE:
                    # If a pct appears on the same line as the SECOND team,
                    # it belongs to the FIRST team (team_a), not team_b.
                    if pct_on_line is not None and prob_a is None:
                        prob_a = pct_on_line
                else:
                    # Third team without flushing: flush and starthi start new block
                    flush_match_if_ready()
                    team_a = team
                    team_b = None
                    prob_a = pct_on_line  # if present, still belongs to first team listed
                    prob_b = None

                i += 1
                continue

            # Percent-only line?
            pct_only = parse_pct_line(raw)
            if pct_only is not None:
                # In the observed export, this line is commonly the SECOND team's pct.
                # Assign in order of missing: prob_a then prob_b.
                if prob_a is None:
                    prob_a = pct_only
                elif prob_b is None:
                    prob_b = pct_only

                flush_match_if_ready()
                i += 1
                continue

            # Otherwise ignore odds/market/noise
            i += 1
            continue

        # No date/time context: ignore
        i += 1

    flush_match_if_ready()
    return out_by_date


def write_outputs(rows_by_date: Dict[str, List[Dict[str, str]]], league: str) -> None:
    if not rows_by_date:
        return

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


def main() -> None:
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")

    input_files = sorted(INPUT_DIR.glob("win_prob_*.csv"))
    if not input_files:
        print("No input files found matching docs/win/win_prob_*.csv")
        return

    for path in input_files:
        league = detect_league(path.name)
        try:
            rows_by_date = clean_one_file(path)
        except Exception as e:
            print(f"ERROR parsing {path.name}: {e}")
            continue

        if not rows_by_date:
            print(f"Parsed 0 games from {path.name} (no output written)")
            continue

        write_outputs(rows_by_date, league)


if __name__ == "__main__":
    main()
