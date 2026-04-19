from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule"
    "?sportId=1&date={date}&hydrate=probablePitcher"
)
LIVE_URL = "https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"

OUTPUT_DIR = Path("docs/win/baseball/00_intake/mlb_raw")

CSV_HEADERS = [
    "gamePk",
    "gameGuid",
    "game_date",
    "game_time",
    "venue_id",
    "doubleheader",
    "gameNumber",
    "home_team_id",
    "away_team_id",
    "home_pitcher_id",
    "away_pitcher_id",
    "day_night",
    "home_bat_1_id",
    "home_bat_2_id",
    "home_bat_3_id",
    "home_bat_4_id",
    "home_bat_5_id",
    "home_bat_6_id",
    "home_bat_7_id",
    "home_bat_8_id",
    "home_bat_9_id",
    "away_bat_1_id",
    "away_bat_2_id",
    "away_bat_3_id",
    "away_bat_4_id",
    "away_bat_5_id",
    "away_bat_6_id",
    "away_bat_7_id",
    "away_bat_8_id",
    "away_bat_9_id",
]


def fetch_json(url: str) -> dict:
    req_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        with urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error for {url}: {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"URL error for {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON returned for {url}") from exc


def safe_get(mapping: dict, *keys, default=""):
    current = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current or current[key] is None:
            return default
        current = current[key]
    return current


def batting_slot(batting_order: list, idx: int) -> str:
    if idx < len(batting_order):
        return batting_order[idx]
    return ""


def build_row(game: dict, live: dict) -> dict:
    home_batting_order = safe_get(
        live, "liveData", "boxscore", "teams", "home", "battingOrder", default=[]
    )
    away_batting_order = safe_get(
        live, "liveData", "boxscore", "teams", "away", "battingOrder", default=[]
    )

    if not isinstance(home_batting_order, list):
        home_batting_order = []
    if not isinstance(away_batting_order, list):
        away_batting_order = []

    row = {
        "gamePk": safe_get(game, "gamePk"),
        "gameGuid": safe_get(game, "gameGuid"),
        "game_date": safe_get(game, "officialDate"),
        "game_time": safe_get(game, "gameDate"),
        "venue_id": safe_get(game, "venue", "id"),
        "doubleheader": safe_get(game, "doubleHeader"),
        "gameNumber": safe_get(game, "gameNumber"),
        "home_team_id": safe_get(game, "teams", "home", "team", "id"),
        "away_team_id": safe_get(game, "teams", "away", "team", "id"),
        "home_pitcher_id": safe_get(live, "gameData", "probablePitchers", "home", "id"),
        "away_pitcher_id": safe_get(live, "gameData", "probablePitchers", "away", "id"),
        "day_night": safe_get(game, "dayNight"),
        "home_bat_1_id": batting_slot(home_batting_order, 0),
        "home_bat_2_id": batting_slot(home_batting_order, 1),
        "home_bat_3_id": batting_slot(home_batting_order, 2),
        "home_bat_4_id": batting_slot(home_batting_order, 3),
        "home_bat_5_id": batting_slot(home_batting_order, 4),
        "home_bat_6_id": batting_slot(home_batting_order, 5),
        "home_bat_7_id": batting_slot(home_batting_order, 6),
        "home_bat_8_id": batting_slot(home_batting_order, 7),
        "home_bat_9_id": batting_slot(home_batting_order, 8),
        "away_bat_1_id": batting_slot(away_batting_order, 0),
        "away_bat_2_id": batting_slot(away_batting_order, 1),
        "away_bat_3_id": batting_slot(away_batting_order, 2),
        "away_bat_4_id": batting_slot(away_batting_order, 3),
        "away_bat_5_id": batting_slot(away_batting_order, 4),
        "away_bat_6_id": batting_slot(away_batting_order, 5),
        "away_bat_7_id": batting_slot(away_batting_order, 6),
        "away_bat_8_id": batting_slot(away_batting_order, 7),
        "away_bat_9_id": batting_slot(away_batting_order, 8),
    }
    return row


def load_existing_game_pks(out_path: Path) -> set:
    """Return the set of gamePk values already written to the file."""
    if not out_path.exists():
        return set()
    with out_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["gamePk"] for row in reader}


def main() -> int:
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = OUTPUT_DIR / f"{target_date.replace('-', '_')}_mlb_raw.csv"

    # Load already-written gamePks so we don't duplicate rows
    existing_pks = load_existing_game_pks(out_path)
    file_exists = out_path.exists()

    schedule = fetch_json(SCHEDULE_URL.format(date=target_date))
    dates = schedule.get("dates", [])
    games = dates[0].get("games", []) if dates else []

    rows = []
    for game in games:
        detailed_state = safe_get(game, "status", "detailedState")
        if detailed_state not in {"Pre-Game", "Scheduled"}:
            continue

        game_pk = str(safe_get(game, "gamePk"))
        if not game_pk or game_pk in existing_pks:
            continue

        live = fetch_json(LIVE_URL.format(game_pk=game_pk))
        rows.append(build_row(game, live))

    # Append mode: write header only if the file is new
    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(out_path.as_posix())
    print(f"rows_written={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
