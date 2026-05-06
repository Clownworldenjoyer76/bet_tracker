#!/usr/bin/env python3
# docs/win/soccer/scripts/00_intake/manual_soccer_pred.py

import argparse
import csv
import re
from pathlib import Path


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

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$", re.IGNORECASE)
RECORD_RE = re.compile(r"\s*\([^)]*\)\s*$")

IGNORE_LINES = {
    "Time\tTeams\tWin\tDraw\tBest",
    "ML\tGoals\tTotal",
    "Goals\tBest",
    "O/U\tBet",
    "Value\tMore Details",
}


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


def normalize_match_date(value: str) -> str:
    value = (value or "").strip()

    if not DATE_RE.match(value):
        raise ValueError(f"Invalid match date format: {value}")

    month, day, year = value.split("/")
    return f"{year}_{month.zfill(2)}_{day.zfill(2)}"


def normalize_match_time(value: str) -> str:
    value = (value or "").strip().upper()

    if not TIME_RE.match(value):
        raise ValueError(f"Invalid match time format: {value}")

    time_part, ampm = value.split()
    hour, minute = time_part.split(":")

    return f"{hour.zfill(2)}:{minute} {ampm}"


def clean_team(value: str) -> str:
    value = (value or "").strip()
    value = RECORD_RE.sub("", value)
    return value.strip()


def split_tabs(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split("\t") if part.strip()]


def read_raw_lines(raw_file: Path) -> list[str]:
    text = raw_file.read_text(encoding="utf-8", errors="replace")
    return text.splitlines()


def clean_raw_lines(raw_lines: list[str]) -> list[str]:
    cleaned = []

    for line in raw_lines:
        line = line.strip()

        if not line:
            continue

        if line in IGNORE_LINES:
            continue

        cleaned.append(line)

    return cleaned


def parse_game_block(lines: list[str], start_index: int, league_value: str) -> tuple[dict, int]:
    match_date_raw = lines[start_index]
    match_date = normalize_match_date(match_date_raw)

    try:
        match_time_raw = lines[start_index + 1]
        away_team_raw = lines[start_index + 2]
        home_team_and_away_prob_raw = lines[start_index + 3]
        home_prob_and_draw_prob_raw = lines[start_index + 4]
        away_xg_raw = lines[start_index + 5]
        home_xg_and_total_raw = lines[start_index + 6]
    except IndexError:
        raise ValueError(f"Incomplete game block starting at raw date line: {match_date_raw}")

    match_time = normalize_match_time(match_time_raw)

    away_team = clean_team(away_team_raw)

    home_team_parts = split_tabs(home_team_and_away_prob_raw)
    if len(home_team_parts) < 2:
        raise ValueError(f"Could not parse home_team and away_prob from: {home_team_and_away_prob_raw}")

    home_team = clean_team(home_team_parts[0])
    away_prob = home_team_parts[1]

    prob_parts = split_tabs(home_prob_and_draw_prob_raw)
    if len(prob_parts) < 2:
        raise ValueError(f"Could not parse home_prob and draw_prob from: {home_prob_and_draw_prob_raw}")

    home_prob = prob_parts[0]
    draw_prob = prob_parts[1]

    away_xg = away_xg_raw.strip()

    xg_parts = split_tabs(home_xg_and_total_raw)
    if len(xg_parts) < 2:
        raise ValueError(f"Could not parse home_xg and expected_total_goals from: {home_xg_and_total_raw}")

    home_xg = xg_parts[0]
    expected_total_goals = xg_parts[1]

    row = {
        "sport": "soccer",
        "league": league_value,
        "match_date": match_date,
        "match_time": match_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_prob": home_prob,
        "draw_prob": draw_prob,
        "away_prob": away_prob,
        "home_xg": home_xg,
        "away_xg": away_xg,
        "expected_total_goals": expected_total_goals,
    }

    return row, start_index + 7


def parse_rows(raw_lines: list[str], league_value: str) -> list[dict]:
    lines = clean_raw_lines(raw_lines)
    rows = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if DATE_RE.match(line):
            row, next_index = parse_game_block(lines, i, league_value)
            rows.append(row)
            i = next_index
        else:
            i += 1

    return rows


def group_rows_by_match_date(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = {}

    for row in rows:
        match_date = row["match_date"]
        grouped.setdefault(match_date, []).append(row)

    return grouped


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


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

    if not market_path_value:
        raise ValueError("Market value is empty after cleanup")

    if not league_value:
        raise ValueError("League value is empty after cleanup")

    raw_lines = read_raw_lines(raw_file)
    rows = parse_rows(raw_lines, league_value)

    if not rows:
        raise ValueError("No soccer prediction rows were parsed from raw input")

    grouped_rows = group_rows_by_match_date(rows)

    out_dir = BASE_OUT_DIR / market_path_value

    for match_date, date_rows in grouped_rows.items():
        csv_path = out_dir / f"{match_date}_{market_path_value}.csv"
        write_csv(csv_path, date_rows)
        print(f"WROTE CSV: {csv_path} ({len(date_rows)} rows)")


if __name__ == "__main__":
    main()
