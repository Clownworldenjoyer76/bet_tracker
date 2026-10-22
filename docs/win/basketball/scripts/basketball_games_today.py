
#!/usr/bin/env python3
"""Merge basketball market CSVs into one games-today CSV per league and date.

All paths are relative to the working directory. Run from the repository root.
Requires only the Python standard library.
"""

import csv
import re
from pathlib import Path

INPUT_ROOT = Path("docs/win/basketball/01_merge")
OUTPUT_ROOT = Path("frontend/data/index_home/basketball")
LEAGUES = ("WNBA", "NBA", "NCAAM")
MARKETS = ("spread", "total", "moneyline")
DATE_PATTERN = re.compile(r"\d{4}_\d{2}_\d{2}\Z")


def input_path(league: str, market: str, date: str) -> Path:
    return INPUT_ROOT / league.lower() / market / f"{date}_{league}_{market}.csv"


def available_dates(league: str) -> list[str]:
    dates = set()
    for market in MARKETS:
        suffix = f"_{league}_{market}.csv"
        for path in (INPUT_ROOT / league.lower() / market).glob(f"*{suffix}"):
            date = path.name[: -len(suffix)]
            if path.is_file() and DATE_PATTERN.fullmatch(date):
                dates.add(date)
    return sorted(dates)


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields or "game_id" not in fields or len(fields) != len(set(fields)):
            raise ValueError(f"Invalid or duplicate CSV headers in {path}")

        rows = []
        seen_ids = set()
        for line_no, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Unexpected extra CSV columns in {path}, line {line_no}")
            game_id = (row.get("game_id") or "").strip()
            if not game_id:
                raise ValueError(f"Missing game_id in {path}, line {line_no}")
            if game_id in seen_ids:
                raise ValueError(f"Duplicate game_id {game_id} in {path}")
            seen_ids.add(game_id)
            rows.append(row)

    return fields, rows


def combine(league: str, date: str) -> int:
    fields: list[str] = []
    games: dict[str, dict[str, str]] = {}

    for market in MARKETS:
        source = input_path(league, market, date)
        source_fields, source_rows = load_csv(source)
        for field in source_fields:
            if field not in fields:
                fields.append(field)
        for row in source_rows:
            game_id = row["game_id"].strip()
            combined = games.setdefault(game_id, {})
            for field, value in row.items():
                value = value or ""
                previous = combined.get(field, "")
                if previous and value and previous != value:
                    raise ValueError(
                        f"Conflicting value: {league} {date} game_id={game_id} "
                        f"column={field!r}, existing={previous!r}, {market}={value!r}"
                    )
                if value or field not in combined:
                    combined[field] = value

    destination = OUTPUT_ROOT / league / f"{date}_{league}_games_today.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(games.values())

    print(f"WROTE {destination} ({len(games)} games)")
    return len(games)


def main() -> None:
    output_files = 0
    for league in LEAGUES:
        for date in available_dates(league):
            missing = [market for market in MARKETS if not input_path(league, market, date).is_file()]
            if missing:
                print(f"SKIP {league} {date}: missing {', '.join(missing)} CSV(s)")
                continue
            combine(league, date)
            output_files += 1
    print(f"DONE: {output_files} CSV file(s) written")


if __name__ == "__main__":
    main()
