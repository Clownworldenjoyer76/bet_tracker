#!/usr/bin/env python3
"""Merge MLB total, moneyline, and run-line CSVs into one CSV per date."""

import argparse
import csv
import os
import re
import tempfile
from pathlib import Path

SOURCE_DIR = Path("docs/win/baseball/mlb/01_merge")
OUTPUT_DIR = Path("frontend/data/index_home")
MARKETS = ("total", "moneyline", "run_line")
SOURCE_PATTERN = re.compile(r"^(\d{4}_\d{2}_\d{2})_mlb_(total|moneyline|run_line)\.csv$")


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "game_id" not in reader.fieldnames:
            raise ValueError(f"Missing game_id header: {path}")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"Duplicate headers: {path}")
        rows = list(reader)

    seen = set()
    for row in rows:
        if None in row:
            raise ValueError(f"Row contains more fields than headers: {path}")
        game_id = (row.get("game_id") or "").strip()
        if not game_id:
            raise ValueError(f"Blank game_id: {path}")
        if game_id in seen:
            raise ValueError(f"Duplicate game_id {game_id}: {path}")
        seen.add(game_id)
    return reader.fieldnames, rows


def merge_date(date: str, source_dir: Path, output_dir: Path):
    columns = []
    merged = {}

    for market in MARKETS:
        path = source_dir / f"{date}_mlb_{market}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Required input not found: {path}")
        headers, rows = read_csv(path)
        for header in headers:
            if header not in columns:
                columns.append(header)

        for row in rows:
            game_id = row["game_id"].strip()
            combined = merged.setdefault(game_id, {})
            for header, incoming in row.items():
                incoming = incoming or ""
                existing = combined.get(header, "")
                if existing and incoming and existing != incoming:
                    raise ValueError(
                        f"Conflicting values for date={date}, game_id={game_id}, "
                        f"column={header}: {existing!r} vs {incoming!r} ({path.name})"
                    )
                if incoming or header not in combined:
                    combined[header] = incoming

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{date}_mlb_games_today.csv"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output_dir,
            prefix=f".{date}_", suffix=".tmp", delete=False
        ) as stream:
            temp_path = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for row in merged.values():
                writer.writerow(row)
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    print(f"{destination}: {len(merged)} games")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path,
        default=Path(__file__).resolve().parents[5],
        help="Root containing docs/win/baseball/mlb/01_merge"
    )
    parser.add_argument(
        "--output-root", type=Path, required=True,
        help="Root containing frontend/data/index_home"
    )
    args = parser.parse_args()

    source_dir = args.source_root.resolve() / SOURCE_DIR
    output_dir = args.output_root.resolve() / OUTPUT_DIR
    if not source_dir.is_dir():
        parser.error(f"Input directory does not exist: {source_dir}")

    dates = sorted({
        match.group(1)
        for path in source_dir.iterdir() if path.is_file()
        if (match := SOURCE_PATTERN.fullmatch(path.name))
    })
    if not dates:
        parser.error(f"No matching MLB source CSV files found in {source_dir}")

    for date in dates:
        merge_date(date, source_dir, output_dir)


if __name__ == "__main__":
    main()
