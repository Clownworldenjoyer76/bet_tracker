#!/usr/bin/env python3
"""Combine MLB total, moneyline, and run-line CSVs by game_id for each date."""

import csv
import re
from pathlib import Path


INPUT_DIR = Path("docs/win/baseball/mlb/01_merge")
OUTPUT_DIR = Path("frontend/data/baseball/index_home")
MARKETS = ("total", "moneyline", "run_line")
FILENAME = re.compile(r"^(\d{4}_\d{2}_\d{2})_mlb_(total|moneyline|run_line)\.csv$")


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "game_id" not in reader.fieldnames:
            raise ValueError(f"Missing game_id header: {path}")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"Duplicate headers: {path}")

        rows = {}
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Extra fields in {path}, line {row_number}")
            game_id = row["game_id"].strip()
            if not game_id:
                raise ValueError(f"Blank game_id in {path}, line {row_number}")
            if game_id in rows:
                raise ValueError(f"Duplicate game_id {game_id} in {path}")
            rows[game_id] = row

        return reader.fieldnames, rows


def merge_date(date):
    columns = []
    merged = {}

    for market in MARKETS:
        path = INPUT_DIR / f"{date}_mlb_{market}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Required input missing: {path}")

        fields, rows = load_csv(path)
        for field in fields:
            if field not in columns:
                columns.append(field)

        for game_id, row in rows.items():
            output = merged.setdefault(game_id, {})
            for field, value in row.items():
                existing = output.get(field, "")
                if existing and value and existing != value:
                    raise ValueError(
                        f"Conflicting values for date={date}, game_id={game_id}, "
                        f"field={field}: {existing!r} versus {value!r} ({path})"
                    )
                if value and not existing:
                    output[field] = value

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / f"{date}_mlb_games_today.csv"
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(merged.values())
    print(f"Wrote {destination}: {len(merged)} games")


def main():
    if not INPUT_DIR.is_dir():
        raise FileNotFoundError(f"Input directory missing: {INPUT_DIR}")

    dates = sorted(
        {
            match.group(1)
            for path in INPUT_DIR.iterdir()
            if path.is_file() and (match := FILENAME.fullmatch(path.name))
        }
    )
    if not dates:
        raise FileNotFoundError(f"No dated MLB input CSVs found in {INPUT_DIR}")

    for date in dates:
        merge_date(date)


if __name__ == "__main__":
    main()
