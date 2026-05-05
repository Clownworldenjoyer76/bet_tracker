"""
ufc_final_scores.py

Parses raw UFC final scores text dump and writes per-event CSV.

Input (dump.txt):
    Time	Fighters	Win	Best
    ML	Final
    Result	Sportsbook
    Log Loss	DRatings
    Log Loss
    04/25/2026
    09:14 PM	Juan Adrian Luna
    Davey Grant	45.8%
    54.2%
    +100
    -115
    Loss
    Win	-0.66000	-0.61175
    04/25/2026
    08:41 PM	Raoni Barcelos
    Montel Jackson	34.9%
    65.1%
    +180
    -200
    Win
    Loss	-1.05317	-1.05245

Output:
    docs/win/mma/ufc/manual_files/{YYYY_MM_DD}_ufc.csv

CSV format:
    match_date,fighter_1,fighter_2,win_prob_1,win_prob_2,
    moneyline_fighter_1,moneyline_fighter_2,result_fighter_1,result_fighter_2
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

OUT_DIR = Path("docs/win/mma/ufc/manual_files")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DATE_RE       = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")
PROB_RE       = re.compile(r"(\d+\.?\d*)\s*%")
MONEYLINE_RE  = re.compile(r"^\s*([+-]\d+)\s*$")
RESULT_TOKENS = {"Win", "Loss", "Draw", "NC"}


def normalize_lines(text: str) -> list[str]:
    """Split on newlines AND tabs, since multi-value rows arrive tab-separated."""
    raw_lines = text.splitlines()
    out = []
    for line in raw_lines:
        for part in line.split("\t"):
            stripped = part.strip()
            if stripped:
                out.append(stripped)
    return out


def is_header_token(s: str) -> bool:
    s_norm = s.strip().lower()
    return s_norm in {
        "time", "fighters", "win", "best", "ml",
        "final", "result", "sportsbook", "log loss", "dratings",
    }


def find_match_blocks(lines: list[str]) -> list[list[str]]:
    """A match block starts at a date line and includes all lines until the next date."""
    blocks = []
    current = []
    current_date = None

    for line in lines:
        if is_header_token(line):
            continue

        m = DATE_RE.match(line)
        if m:
            if current and current_date:
                blocks.append((current_date, current))
            current = []
            current_date = (m.group(3), m.group(1), m.group(2))  # (year, mm, dd)
            continue

        if current_date is not None:
            current.append(line)

    if current and current_date:
        blocks.append((current_date, current))

    return blocks


def parse_block(block_lines: list[str]) -> dict | None:
    """
    Block lines look like:
        ['09:14 PM', 'Juan Adrian Luna', 'Davey Grant', '45.8%',
         '54.2%', '+100', '-115', 'Loss', 'Win', '-0.66000', '-0.61175']

    The first line is the time (e.g. '09:14 PM').
    Skip times. Then collect names, percents, moneylines, results in order.
    """
    fighters = []
    probs = []
    moneylines = []
    results = []

    time_re = re.compile(r"^\d{1,2}:\d{2}\s*(?:AM|PM)$", re.IGNORECASE)

    for line in block_lines:
        line = line.strip()
        if not line:
            continue

        # Skip time lines
        if time_re.match(line):
            continue

        # Skip log loss numbers (decimals with optional minus sign, no plus)
        if re.match(r"^-?\d+\.\d+$", line):
            continue

        # Moneyline (e.g. +100 or -115)
        if MONEYLINE_RE.match(line):
            moneylines.append(line)
            continue

        # Win probability (e.g. 45.8%)
        prob_match = PROB_RE.search(line)
        if prob_match and "%" in line:
            probs.append(round(float(prob_match.group(1)) / 100, 3))
            continue

        # Result token
        if line in RESULT_TOKENS:
            results.append(line)
            continue

        # Otherwise treat as fighter name
        fighters.append(line)

    if len(fighters) < 2 or len(probs) < 2 or len(moneylines) < 2 or len(results) < 2:
        return None

    return {
        "fighter_1": fighters[0],
        "fighter_2": fighters[1],
        "win_prob_1": probs[0],
        "win_prob_2": probs[1],
        "moneyline_fighter_1": moneylines[0],
        "moneyline_fighter_2": moneylines[1],
        "result_fighter_1": results[0],
        "result_fighter_2": results[1],
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: ufc_final_scores.py <dump.txt>")
        return 1

    dump_path = Path(sys.argv[1])
    if not dump_path.exists():
        print(f"File not found: {dump_path}")
        return 1

    text = dump_path.read_text(encoding="utf-8")
    lines = normalize_lines(text)
    blocks = find_match_blocks(lines)

    if not blocks:
        print("No match blocks found.")
        return 1

    fights_by_date = defaultdict(list)

    for (year, mm, dd), block_lines in blocks:
        date_key = f"{year}_{mm}_{dd}"
        parsed = parse_block(block_lines)
        if not parsed:
            print(f"  Skipped malformed block for {date_key}")
            continue
        parsed["match_date"] = date_key
        fights_by_date[date_key].append(parsed)

    fieldnames = [
        "match_date", "fighter_1", "fighter_2",
        "win_prob_1", "win_prob_2",
        "moneyline_fighter_1", "moneyline_fighter_2",
        "result_fighter_1", "result_fighter_2",
    ]

    written = 0
    for date_key, fights in sorted(fights_by_date.items()):
        outfile = OUT_DIR / f"{date_key}_ufc.csv"
        with outfile.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for fight in fights:
                writer.writerow({k: fight.get(k, "") for k in fieldnames})
        print(f"WROTE {outfile} ({len(fights)} fights)")
        written += 1

    if written == 0:
        print("No CSV files written.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
