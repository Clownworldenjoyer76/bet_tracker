#!/usr/bin/env python3

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://api.sportsrc.org/v2/"
OUTPUT_DIR = Path("docs/win/final_scores/results/soccer/final_scores")

LEAGUE_MAP = {
    "LaLiga": "laliga",
    "Premier League": "epl",
    "MLS": "mls",
    "Ligue 1": "ligue1",
    "Serie A": "seria",
    "Bundesliga": "bundesliga",
}

HEADERS = [
    "sport",
    "league",
    "market",
    "game_date",
    "match_time",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
]


def get_target_date() -> str:
    env_date = os.getenv("TARGET_DATE", "").strip()
    if env_date:
        return env_date

    eastern = ZoneInfo("America/New_York")
    return (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")


def format_game_date(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y_%m_%d")


def format_match_time(timestamp_ms):
    if timestamp_ms in (None, "", 0):
        return ""

    eastern = ZoneInfo("America/New_York")
    dt_eastern = datetime.fromtimestamp(int(timestamp_ms) / 1000, eastern)
    return dt_eastern.strftime("%I:%M %p")


def fetch_finished_matches(date_str: str, api_key: str) -> dict:
    params = {
        "type": "matches",
        "sport": "football",
        "status": "finished",
        "date": date_str,
    }
    headers = {
        "X-API-KEY": api_key,
    }

    response = requests.get(API_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if not data.get("success"):
        raise RuntimeError(f"API returned unsuccessful response: {data}")

    return data


def build_rows(payload: dict) -> list[dict]:
    rows = []
    api_date = payload.get("filters", {}).get("date", "")
    game_date = format_game_date(api_date) if api_date else ""

    for league_block in payload.get("data", []):
        league_info = league_block.get("league", {})
        api_league_name = league_info.get("name", "")

        if api_league_name not in LEAGUE_MAP:
            continue

        mapped_league = LEAGUE_MAP[api_league_name]

        for match in league_block.get("matches", []):
            teams = match.get("teams", {})
            home_team = teams.get("home", {}).get("name", "")
            away_team = teams.get("away", {}).get("name", "")
            current_score = match.get("score", {}).get("current", {})

            rows.append({
                "sport": "soccer",
                "league": mapped_league,
                "market": "",
                "game_date": game_date,
                "match_time": format_match_time(match.get("timestamp")),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": current_score.get("home", ""),
                "away_score": current_score.get("away", ""),
            })

    return rows


def write_csv(rows: list[dict], game_date: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{game_date}_soccer_final_scores.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def main():
    api_key = os.environ["SPORTSRC_API"]
    target_date = get_target_date()

    payload = fetch_finished_matches(target_date, api_key)
    rows = build_rows(payload)
    game_date = format_game_date(target_date)

    output_path = write_csv(rows, game_date)
    print(f"WROTE {output_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
