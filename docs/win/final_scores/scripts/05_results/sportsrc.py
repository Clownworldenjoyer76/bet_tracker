#!/usr/bin/env python3

import csv
import json
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://api.sportsrc.org/v2/"
OUTPUT_DIR = Path("docs/win/final_scores/results/soccer/final_scores")
ERROR_DIR = Path("docs/win/final_scores/errors")
LOG_FILE = ERROR_DIR / "soccer_final_scores_log.txt"

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


def now_utc_str() -> str:
    return datetime.now(ZoneInfo("UTC")).isoformat()


def log(message: str, level: str = "INFO") -> None:
    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now_utc_str()} | {level:<5} | {message}\n")


def reset_log() -> None:
    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== soccer_final_scores RUN {now_utc_str()} ===\n")


def get_target_date() -> str:
    env_date = os.getenv("TARGET_DATE", "").strip()
    if env_date:
        log(f"TARGET_DATE env provided: {env_date}")
        return env_date

    eastern = ZoneInfo("America/New_York")
    computed = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    log(f"TARGET_DATE env blank; using previous day in America/New_York: {computed}")
    return computed


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

    safe_headers = {"X-API-KEY": "***REDACTED***"}
    log(f"REQUEST URL: {API_URL}")
    log(f"REQUEST PARAMS: {json.dumps(params, ensure_ascii=False)}")
    log(f"REQUEST HEADERS: {json.dumps(safe_headers, ensure_ascii=False)}")

    response = requests.get(API_URL, params=params, headers=headers, timeout=30)

    log(f"RESPONSE STATUS: {response.status_code}")
    log(f"RESPONSE URL: {response.url}")

    response.raise_for_status()

    data = response.json()
    log(f"API success flag: {data.get('success')}")
    log(f"API filters: {json.dumps(data.get('filters', {}), ensure_ascii=False)}")
    log(f"API total_leagues: {data.get('total_leagues', 0)}")
    log(f"API total_matches: {data.get('total_matches', 0)}")

    league_names = [
        block.get("league", {}).get("name", "")
        for block in data.get("data", [])
    ]
    log(f"API leagues returned: {json.dumps(league_names, ensure_ascii=False)}")

    if not data.get("success"):
        raise RuntimeError(f"API returned unsuccessful response: {data}")

    return data


def build_rows(payload: dict) -> list[dict]:
    rows = []
    api_date = payload.get("filters", {}).get("date", "")
    game_date = format_game_date(api_date) if api_date else ""

    returned_leagues = []
    kept_leagues = []

    for league_block in payload.get("data", []):
        league_info = league_block.get("league", {})
        api_league_name = league_info.get("name", "")
        returned_leagues.append(api_league_name)

        if api_league_name not in LEAGUE_MAP:
            continue

        kept_leagues.append(api_league_name)
        mapped_league = LEAGUE_MAP[api_league_name]

        matches = league_block.get("matches", [])
        log(f"KEEPING league '{api_league_name}' as '{mapped_league}' with {len(matches)} matches")

        for match in matches:
            teams = match.get("teams", {})
            home_team = teams.get("home", {}).get("name", "")
            away_team = teams.get("away", {}).get("name", "")
            current_score = match.get("score", {}).get("current", {})

            row = {
                "sport": "soccer",
                "league": mapped_league,
                "market": "",
                "game_date": game_date,
                "match_time": format_match_time(match.get("timestamp")),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": current_score.get("home", ""),
                "away_score": current_score.get("away", ""),
            }
            rows.append(row)

    skipped_leagues = [lg for lg in returned_leagues if lg not in LEAGUE_MAP]

    log(f"TARGET leagues configured: {json.dumps(list(LEAGUE_MAP.keys()), ensure_ascii=False)}")
    log(f"Returned leagues count: {len(returned_leagues)}")
    log(f"Matched leagues count: {len(kept_leagues)}")
    log(f"Matched leagues: {json.dumps(kept_leagues, ensure_ascii=False)}")
    log(f"Skipped leagues: {json.dumps(skipped_leagues, ensure_ascii=False)}")
    log(f"Rows built: {len(rows)}")

    return rows


def write_csv(rows: list[dict], game_date: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{game_date}_soccer_final_scores.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    log(f"WROTE CSV: {output_path} ({len(rows)} rows)")
    return output_path


def main():
    reset_log()

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ERROR_DIR.mkdir(parents=True, exist_ok=True)

        script_path = Path(__file__).resolve()
        log(f"SCRIPT PATH: {script_path}")
        log(f"CWD: {Path.cwd()}")

        api_key = os.environ.get("SPORTSRC_API", "").strip()
        if not api_key:
            raise RuntimeError("Missing SPORTSRC_API environment variable")

        log("SPORTSRC_API env found")
        target_date = get_target_date()
        log(f"Final target date: {target_date}")

        payload = fetch_finished_matches(target_date, api_key)
        rows = build_rows(payload)
        game_date = format_game_date(target_date)
        output_path = write_csv(rows, game_date)

        if len(rows) == 0:
            log("CSV has only headers because zero rows matched target leagues for this date", "WARN")

        print(f"WROTE {output_path} ({len(rows)} rows)")

    except Exception as e:
        log(f"FATAL ERROR: {e}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        raise


if __name__ == "__main__":
    main()
