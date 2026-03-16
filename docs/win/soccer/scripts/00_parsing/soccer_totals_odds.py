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

DATE_TIME_RE = re.compile(
    r"(?:(\d{1,2})/(\d{1,2})\s*,\s*)?(\d{1,2}):(\d{2})([ap])",
    re.IGNORECASE,
)


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(EASTERN_TZ).isoformat()} | {msg}\n")


def read_github_event_inputs():
    path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not path:
        return {}
    try:
        payload = json.loads(Path(path).read_text())
        return payload.get("inputs", {})
    except Exception:
        return {}


def get_args():
    p = argparse.ArgumentParser()
    p.add_argument("--league", default="")
    p.add_argument("--market", default="")
    p.add_argument("--raw-text", default="")
    p.add_argument("--raw-file", default="")
    return p.parse_args()


def get_runtime_inputs():
    args = get_args()
    event_inputs = read_github_event_inputs()

    league = (
        args.league
        or os.environ.get("INPUT_LEAGUE", "")
        or event_inputs.get("league", "")
    )

    market = (
        args.market
        or os.environ.get("INPUT_MARKET", "")
        or event_inputs.get("market", "")
    )

    raw = (
        args.raw_text
        or os.environ.get("INPUT_RAW_TEXT", "")
        or event_inputs.get("raw_text", "")
    )

    if not raw and args.raw_file:
        raw = Path(args.raw_file).read_text()

    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()

    return league.strip(), market.strip(), raw


def today_eastern():
    return datetime.now(EASTERN_TZ).strftime("%Y_%m_%d")


def parse_match_datetime(line):
    m = DATE_TIME_RE.search(line)
    if not m:
        raise ValueError(f"Could not parse match date/time line: {line}")

    month, day, hour, minute, ap = m.groups()

    if month and day:
        date = f"{datetime.now(EASTERN_TZ).year}_{int(month):02d}_{int(day):02d}"
    else:
        date = today_eastern()

    hour = int(hour)
    minute = int(minute)

    if ap.lower() == "p" and hour != 12:
        hour += 12
    if ap.lower() == "a" and hour == 12:
        hour = 0

    time = f"{hour:02d}:{minute:02d}"

    return date, time


def looks_like_datetime(line):
    return bool(DATE_TIME_RE.search(line))


def split_lines(raw):
    return [l.strip() for l in raw.splitlines() if l.strip()]


def parse_games(lines):
    games = []
    i = 0

    while i < len(lines):

        if lines[i] == "Over":
            break

        away = lines[i + 1]
        home = lines[i + 3]
        dt = lines[i + 4]

        if not looks_like_datetime(dt):
            raise ValueError(f"Expected datetime line got {dt}")

        date, time = parse_match_datetime(dt)

        games.append(
            dict(
                match_date=date,
                match_time=time,
                home_team=home,
                away_team=away,
            )
        )

        i += 5

    return games, i


def parse_snippet(lines, i):

    over = lines[i]
    line1 = lines[i + 1]
    odds1 = lines[i + 2]
    under = lines[i + 3]
    line2 = lines[i + 4]
    odds2 = lines[i + 5]

    if over != "Over":
        raise ValueError("Expected Over")
    if under != "Under":
        raise ValueError("Expected Under")

    return (
        dict(line=line1, over=odds1, under=odds2),
        i + 6,
    )


def parse_odds_groups(lines, start, market):

    snippets = []
    i = start

    while i < len(lines):

        if lines[i] != "Over":
            raise ValueError(f"Unexpected token {lines[i]}")

        s, i = parse_snippet(lines, i)
        snippets.append(s)

    market_key = market.lower()

    if market_key in {"bundesliga", "laliga"}:
        block_size = 4
    else:
        block_size = 5

    if len(snippets) % block_size != 0:
        raise ValueError(
            f"Odds snippets count ({len(snippets)}) is not divisible by {block_size}."
        )

    groups = []

    for x in range(0, len(snippets), block_size):

        block = snippets[x : x + block_size]

        row = dict(
            over25_american="",
            under25_american="",
            over35_american="",
            under35_american="",
        )

        for s in block:

            if s["line"] == "2.5":
                row["over25_american"] = s["over"]
                row["under25_american"] = s["under"]
                break

            if s["line"] == "3.5":
                row["over35_american"] = s["over"]
                row["under35_american"] = s["under"]
                break

        groups.append(row)

    return groups


def write_files(rows, market):

    by_date = defaultdict(list)

    for r in rows:
        by_date[r["match_date"]].append(r)

    m = re.sub(r"\W+", "_", market)

    written = []

    for d, rws in by_date.items():

        out = OUTPUT_DIR / f"soccer_{d}_{m}_totals.csv"
        tmp = out.with_suffix(".tmp")

        with open(tmp, "w", newline="", encoding="utf-8") as f:

            w = csv.DictWriter(f, FIELDNAMES)
            w.writeheader()

            for r in rws:
                w.writerow(r)

        tmp.replace(out)
        written.append(out)

    return written


def main():

    league, market, raw = get_runtime_inputs()

    if not raw:
        print("ERROR: Missing raw_text")
        return 1

    lines = split_lines(raw)

    games, idx = parse_games(lines)

    odds = parse_odds_groups(lines, idx, market)

    if len(games) != len(odds):
        raise ValueError(
            f"Game/odds mismatch {len(games)} vs {len(odds)}"
        )

    rows = []

    for g, o in zip(games, odds):

        rows.append(
            dict(
                league=league,
                market=market,
                match_date=g["match_date"],
                match_time=g["match_time"],
                home_team=g["home_team"],
                away_team=g["away_team"],
                over25_american=o["over25_american"],
                under25_american=o["under25_american"],
                over35_american=o["over35_american"],
                under35_american=o["under35_american"],
            )
        )

    files = write_files(rows, market)

    for f in files:
        print(f"Wrote {f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
