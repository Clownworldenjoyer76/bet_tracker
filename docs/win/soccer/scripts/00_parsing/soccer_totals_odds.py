#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/soccer_totals_odds.py

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# =========================
# PATHS
# =========================
OUTPUT_DIR = Path("docs/win/soccer/00_intake/sportsbook/totals_odds")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = Path("docs/win/soccer/errors/00_parsing")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "soccer_totals_odds.txt"

FIELDNAMES = [
    "league",
    "market",
    "match_date",
    "match_time",
    "home_team",
    "away_team",
    "over25_american",
    "under25_american",
    "over35_american",
    "under35_american",
]

EASTERN_TZ = ZoneInfo("America/New_York")
AMERICAN_ODDS_RE = re.compile(r"^[+-]\d{3,4}$")

# Robust datetime detection
DATE_TIME_RE = re.compile(
    r"(?:(\d{1,2})/(\d{1,2})\s*,\s*)?(\d{1,2}):(\d{2})([ap])",
    re.IGNORECASE,
)


def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(EASTERN_TZ).isoformat()} | {msg}\n")


# =========================
# INPUT HANDLING
# =========================
def read_github_event_inputs() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        return {}

    path = Path(event_path)
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"Could not read GITHUB_EVENT_PATH: {e}")
        return {}

    inputs = payload.get("inputs", {})
    if isinstance(inputs, dict):
        return inputs

    return {}


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default="")
    parser.add_argument("--market", default="")
    parser.add_argument("--raw-text", default="")
    parser.add_argument("--raw-file", default="")
    return parser.parse_args()


def get_runtime_inputs() -> tuple[str, str, str]:
    args = get_args()
    event_inputs = read_github_event_inputs()

    league = (
        args.league
        or os.environ.get("LEAGUE", "")
        or os.environ.get("INPUT_LEAGUE", "")
        or event_inputs.get("league", "")
    ).strip()

    market = (
        args.market
        or os.environ.get("MARKET", "")
        or os.environ.get("INPUT_MARKET", "")
        or event_inputs.get("market", "")
    ).strip()

    raw_text = (
        args.raw_text
        or os.environ.get("RAW_TEXT", "")
        or os.environ.get("INPUT_RAW_TEXT", "")
        or event_inputs.get("raw_text", "")
    )

    if not raw_text and args.raw_file:
        raw_path = Path(args.raw_file)
        if raw_path.exists():
            raw_text = raw_path.read_text(encoding="utf-8")

    if not raw_text and not sys.stdin.isatty():
        raw_text = sys.stdin.read()

    return league, market, raw_text


# =========================
# HELPERS
# =========================
def today_eastern_str() -> str:
    return datetime.now(EASTERN_TZ).strftime("%Y_%m_%d")


def parse_match_datetime(line: str) -> tuple[str, str]:
    line = line.strip()

    m = DATE_TIME_RE.search(line)

    if not m:
        raise ValueError(f"Could not parse match date/time line: {line!r}")

    month, day, hour, minute, ampm = m.groups()

    if month and day:
        match_date = f"{datetime.now(EASTERN_TZ).year}_{int(month):02d}_{int(day):02d}"
    else:
        match_date = today_eastern_str()

    hour = int(hour)
    minute = int(minute)
    ampm = ampm.lower()

    if ampm == "a":
        if hour == 12:
            hour = 0
    else:
        if hour != 12:
            hour += 12

    match_time = f"{hour:02d}:{minute:02d}"

    return match_date, match_time


def looks_like_datetime_line(line: str) -> bool:
    return bool(DATE_TIME_RE.search(line))


def is_odds_token(line: str) -> bool:
    return bool(AMERICAN_ODDS_RE.match(line.strip()))


def safe_filename_market(market: str) -> str:
    market = market.strip()
    market = re.sub(r"\s+", "_", market)
    market = re.sub(r"[^A-Za-z0-9_]", "", market)
    return market


def split_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


# =========================
# GAME BLOCK PARSING
# =========================
def parse_games(lines: list[str]) -> tuple[list[dict], int]:
    games = []
    i = 0

    while i < len(lines):
        if lines[i] == "Over":
            break

        if i + 4 >= len(lines):
            raise ValueError("Incomplete game block in raw input.")

        away_team = lines[i + 1].strip()
        home_team = lines[i + 3].strip()
        dt_line = lines[i + 4].strip()

        if not looks_like_datetime_line(dt_line):
            raise ValueError(f"Expected date/time line, got: {dt_line!r}")

        match_date, match_time = parse_match_datetime(dt_line)

        games.append(
            {
                "match_date": match_date,
                "match_time": match_time,
                "home_team": home_team,
                "away_team": away_team,
            }
        )

        i += 5

    return games, i


# =========================
# ODDS BLOCK PARSING
# =========================
def parse_single_market_snippet(lines: list[str], start_idx: int) -> tuple[dict, int]:
    if start_idx + 5 >= len(lines):
        raise ValueError("Incomplete odds snippet at end of raw input.")

    over_token = lines[start_idx]
    total_line_1 = lines[start_idx + 1].strip()
    over_odds = lines[start_idx + 2].strip()
    under_token = lines[start_idx + 3]
    total_line_2 = lines[start_idx + 4].strip()
    under_odds = lines[start_idx + 5].strip()

    if over_token != "Over":
        raise ValueError(f"Expected 'Over', got {over_token!r}")
    if under_token != "Under":
        raise ValueError(f"Expected 'Under', got {under_token!r}")
    if total_line_1 != total_line_2:
        raise ValueError(
            f"Mismatched total lines in odds snippet: {total_line_1!r} vs {total_line_2!r}"
        )
    if not is_odds_token(over_odds):
        raise ValueError(f"Invalid over odds token: {over_odds!r}")
    if not is_odds_token(under_odds):
        raise ValueError(f"Invalid under odds token: {under_odds!r}")

    snippet = {
        "line": total_line_1,
        "over_odds": over_odds,
        "under_odds": under_odds,
    }
    return snippet, start_idx + 6


def parse_odds_groups(lines: list[str], start_idx: int) -> list[dict]:
    snippets = []
    i = start_idx

    while i < len(lines):
        if lines[i] != "Over":
            raise ValueError(f"Unexpected token in odds section: {lines[i]!r}")

        snippet, i = parse_single_market_snippet(lines, i)
        snippets.append(snippet)

    if len(snippets) % 5 != 0:
        raise ValueError(
            f"Odds snippets count ({len(snippets)}) is not divisible by 5."
        )

    odds_groups = []
    for group_start in range(0, len(snippets), 5):
        group = snippets[group_start : group_start + 5]

        row_odds = {
            "over25_american": "",
            "under25_american": "",
            "over35_american": "",
            "under35_american": "",
        }

        chosen = None
        for snippet in group:
            if snippet["line"] == "2.5":
                chosen = ("2.5", snippet)
                break
            if snippet["line"] == "3.5":
                chosen = ("3.5", snippet)
                break

        if chosen:
            line_value, snippet = chosen
            if line_value == "2.5":
                row_odds["over25_american"] = snippet["over_odds"]
                row_odds["under25_american"] = snippet["under_odds"]
            elif line_value == "3.5":
                row_odds["over35_american"] = snippet["over_odds"]
                row_odds["under35_american"] = snippet["under_odds"]

        odds_groups.append(row_odds)

    return odds_groups


# =========================
# OUTPUT
# =========================
def write_output_files(rows: list[dict], market: str) -> list[Path]:
    written = []
    by_date = defaultdict(list)

    for row in rows:
        by_date[row["match_date"]].append(row)

    filename_market = safe_filename_market(market)

    for match_date, date_rows in by_date.items():
        outfile = OUTPUT_DIR / f"soccer_{match_date}_{filename_market}_totals.csv"
        temp_file = outfile.with_suffix(".tmp")

        with open(temp_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in date_rows:
                writer.writerow(row)

        temp_file.replace(outfile)
        written.append(outfile)

    return written


# =========================
# MAIN
# =========================
def main() -> int:
    league, market, raw_text = get_runtime_inputs()

    if not league:
        log("Missing league input.")
        print("ERROR: Missing league input.", file=sys.stderr)
        return 1

    if not market:
        log("Missing market input.")
        print("ERROR: Missing market input.", file=sys.stderr)
        return 1

    if not raw_text.strip():
        log("Missing raw_text input.")
        print("ERROR: Missing raw_text input.", file=sys.stderr)
        return 1

    lines = split_lines(raw_text)

    try:
        games, odds_start_idx = parse_games(lines)
        odds_groups = parse_odds_groups(lines, odds_start_idx)
    except Exception as e:
        log(f"Parse failure for market={market}: {e}")
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not games:
        log(f"No games parsed for market={market}.")
        print("ERROR: No games parsed.", file=sys.stderr)
        return 1

    if not odds_groups:
        log(f"No odds groups parsed for market={market}.")
        print("ERROR: No odds groups parsed.", file=sys.stderr)
        return 1

    if len(games) != len(odds_groups):
        log(
            f"Game/odds mismatch for market={market}: "
            f"{len(games)} games vs {len(odds_groups)} odds groups"
        )
        print(
            f"ERROR: Parsed {len(games)} games but {len(odds_groups)} odds groups.",
            file=sys.stderr,
        )
        return 1

    rows = []
    for game, odds in zip(games, odds_groups):
        rows.append(
            {
                "league": league,
                "market": market,
                "match_date": game["match_date"],
                "match_time": game["match_time"],
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "over25_american": odds["over25_american"],
                "under25_american": odds["under25_american"],
                "over35_american": odds["over35_american"],
                "under35_american": odds["under35_american"],
            }
        )

    try:
        written_files = write_output_files(rows, market)
    except Exception as e:
        log(f"Write failure for market={market}: {e}")
        print(f"ERROR: Failed to write output files: {e}", file=sys.stderr)
        return 1

    for path in written_files:
        print(f"Wrote {path}")

    log(
        f"Success: market={market} league={league} "
        f"rows={len(rows)} files={len(written_files)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
