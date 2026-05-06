#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


BASE_OUT_DIR = Path("docs/win/soccer/00_intake/predictions")

CSV_HEADERS = [
    "sport",
    "league",
    "match_date",
    "match_time",
    "home_team",
    "away_team",
    "home_prob",
    "draw_prob",
    "away_prob",
    "home_xg",
    "away_xg",
    "expected_total_goals",
]


def clean_market_for_path(value: str) -> str:
    return (
        (value or "")
        .strip()
        .replace("_", "")
        .replace(" ", "")
        .upper()
    )


def clean_market_for_league_value(value: str) -> str:
    return (
        (value or "")
        .strip()
        .replace("_", "")
        .replace(" ", "")
        .lower()
    )


def today_yyyy_mm_dd() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y_%m_%d")


def normalize_match_date(value: str) -> str:
    value = (value or "").strip()

    if not value:
        return today_yyyy_mm_dd()

    value = value.replace("-", "_").replace("/", "_")

    parts = value.split("_")

    if len(parts) != 3:
      raise ValueError(f"Invalid match date format: {value}")

    year, month, day = parts

    if len(year) != 4:
      raise ValueError(f"Invalid match date year: {value}")

    return f"{year}_{month.zfill(2)}_{day.zfill(2)}"


def read_raw_lines(raw_file: Path) -> list[str]:
    text = raw_file.read_text(encoding="utf-8", errors="replace")
    return text.splitlines()


def write_numbered_raw_lines(path: Path, raw_lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        for i, line in enumerate(raw_lines, start=1):
            f.write(f"{i}: {line}\n")


def write_placeholder_csv(path: Path, raw_lines: list[str], league_value: str, match_date: str) -> None:
    non_blank_lines = [line for line in raw_lines if line.strip()]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()

        for _line in non_blank_lines:
            writer.writerow({
                "sport": "soccer",
                "league": league_value,
                "match_date": match_date,
                "match_time": "",
                "home_team": "",
                "away_team": "",
                "home_prob": "",
                "draw_prob": "",
                "away_prob": "",
                "home_xg": "",
                "away_xg": "",
                "expected_total_goals": "",
            })


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--market", required=True)
    parser.add_argument("--raw-file", required=True)
    parser.add_argument("--match-date", default="")

    args = parser.parse_args()

    raw_file = Path(args.raw_file)

    if not raw_file.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_file}")

    market_path_value = clean_market_for_path(args.market)
    league_value = clean_market_for_league_value(args.market)
    match_date = normalize_match_date(args.match_date)

    if not market_path_value:
        raise ValueError("Market value is empty after cleanup")

    if not league_value:
        raise ValueError("League value is empty after cleanup")

    out_dir = BASE_OUT_DIR / market_path_value
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{match_date}_{market_path_value}.csv"
    numbered_raw_path = out_dir / f"{match_date}_{market_path_value}_raw_lines_numbered.txt"

    raw_lines = read_raw_lines(raw_file)

    write_numbered_raw_lines(numbered_raw_path, raw_lines)
    write_placeholder_csv(csv_path, raw_lines, league_value, match_date)

    print(f"WROTE CSV: {csv_path}")
    print(f"WROTE NUMBERED RAW LINES: {numbered_raw_path}")


if __name__ == "__main__":
    main()
