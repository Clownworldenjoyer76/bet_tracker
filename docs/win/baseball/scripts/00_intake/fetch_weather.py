#!/usr/bin/env python3
# docs/win/baseball/scripts/00_intake/fetch_weather.py
#
# Runs ONCE per day after build_games_list.py.
# Reads {date}_games.csv for venue/game_time info,
# calls weatherapi.com once per unique venue+hour combo,
# and writes results to data/weather/{date}_weather.csv.
#
# enrich_game_context.py reads from that cache — it never calls the API.

import os
import traceback
import requests
from datetime import datetime, UTC
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────

BASE_DIR      = Path("docs/win/baseball")
GAMES_DIR     = BASE_DIR / "00_intake/games"
MAPS_DIR      = BASE_DIR / "maps"
WEATHER_DIR   = BASE_DIR / "data/weather"
ERROR_DIR     = BASE_DIR / "errors/00_intake"

WEATHER_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "fetch_weather.txt"

WEATHER_API_KEY = os.environ.get("WEATHER_API", "")

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def _now():
    return datetime.now(UTC).isoformat()


def _log(msg: str, level: str = "INFO"):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{_now()} | {level:<5} | {msg.rstrip()}\n")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def load_venue_map() -> dict:
    """Returns dict: venue_id -> venue row dict."""
    df = pd.read_csv(
        MAPS_DIR / "mlb_venue_ids.csv",
        dtype={"venue_id": str},
        encoding="utf-8-sig"
    )
    df["venue_id"] = df["venue_id"].str.strip()
    return df.set_index("venue_id").to_dict("index")


def book_time_to_utc_approx(game_time_str: str, game_date_str: str, tz_id: str) -> str:
    """
    Convert sportsbook local time (HH:MM:SS) + date + timezone
    to a UTC datetime string for the weather API.
    game_date_str format: YYYY-MM-DD or YYYY_MM_DD
    """
    try:
        date_clean = game_date_str.replace("_", "-")
        dt_local = datetime.strptime(
            f"{date_clean} {game_time_str}", "%Y-%m-%d %H:%M:%S"
        )
        dt_local = dt_local.replace(tzinfo=ZoneInfo(tz_id))
        dt_utc   = dt_local.astimezone(ZoneInfo("UTC"))
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), date_clean, str(dt_local.hour)
    except Exception as e:
        _log(f"Time conversion failed for {game_date_str} {game_time_str} {tz_id}: {e}", "WARN")
        return None, None, None


def call_weather_api(lat: str, lon: str, local_date: str, local_hour: str) -> dict:
    """Call weatherapi.com and return the matched hour data."""
    if not WEATHER_API_KEY:
        _log("WEATHER_API not set — cannot fetch weather", "WARN")
        return {}
    try:
        url = (
            f"http://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}&q={lat},{lon}&days=1&dt={local_date}&hour={local_hour}"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        hour_data = r.json()["forecast"]["forecastday"][0]["hour"][0]
        return {
            "weather_time":   hour_data.get("time"),
            "temp_f":         hour_data.get("temp_f"),
            "wind_mph":       hour_data.get("wind_mph"),
            "wind_dir":       hour_data.get("wind_dir"),
            "gust_mph":       hour_data.get("gust_mph"),
            "precip_in":      hour_data.get("precip_in"),
            "humidity":       hour_data.get("humidity"),
            "chance_of_rain": hour_data.get("chance_of_rain"),
            "will_it_rain":   hour_data.get("will_it_rain"),
        }
    except Exception as e:
        _log(f"Weather API failed for {lat},{lon} {local_date} hr={local_hour}: {e}", "ERROR")
        return {}


# ─────────────────────────────────────────────
# PROCESS ONE DATE
# ─────────────────────────────────────────────

def process_date(date_str: str, venue_map: dict, summary: dict) -> None:
    games_path   = GAMES_DIR / f"{date_str}_games.csv"
    weather_path = WEATHER_DIR / f"{date_str}_weather.csv"

    if not games_path.exists():
        _log(f"{date_str} | games file not found — skipping", "WARN")
        summary["skipped"] += 1
        return

    # If weather file already exists for today, skip entirely
    if weather_path.exists():
        _log(f"{date_str} | weather file already exists — skipping (delete to re-fetch)")
        summary["skipped"] += 1
        return

    games_df = pd.read_csv(games_path, dtype=str)
    _log(f"--- {date_str} | {len(games_df)} games")

    # Build one weather row per game (keyed on venue+hour to avoid duplicate API calls)
    seen_keys  = {}  # cache_key -> weather dict
    output_rows = []

    for _, row in games_df.iterrows():
        game_pk  = row.get("gamePk", "")
        venue_id = str(row.get("venue_id", "")).strip()
        game_time = row.get("game_time", "")   # HH:MM:SS local sportsbook time
        game_date = row.get("game_date", "")

        vinfo     = venue_map.get(venue_id, {})
        roof_type = str(vinfo.get("roof_type", "")).strip().lower()
        lat       = str(vinfo.get("latitude", "")).strip()
        lon       = str(vinfo.get("longitude", "")).strip()
        tz_id     = vinfo.get("time_zone_id", "America/New_York")
        wind_out  = str(vinfo.get("wind_out_direction", "")).strip()

        # Skip domes/indoor — weather not applicable
        weather_applicable = 0 if roof_type in ("dome", "indoor") else 1

        weather = {}
        wind_blowing_out = None

        if weather_applicable and lat and lon and game_time:
            # game_time from sportsbook is already local — derive local_date and hour
            try:
                date_clean = game_date.replace("_", "-")
                dt_local   = datetime.strptime(f"{date_clean} {game_time}", "%Y-%m-%d %H:%M:%S")
                local_date = dt_local.strftime("%Y-%m-%d")
                local_hour = str(dt_local.hour)
            except Exception as e:
                _log(f"  {game_pk} time parse failed: {e}", "WARN")
                local_date = local_hour = None

            if local_date and local_hour:
                cache_key = f"{lat}_{lon}_{local_date}_{local_hour}"

                if cache_key in seen_keys:
                    weather = seen_keys[cache_key]
                    _log(f"  {game_pk} | reused weather for {cache_key}")
                else:
                    weather = call_weather_api(lat, lon, local_date, local_hour)
                    if weather:
                        seen_keys[cache_key] = weather
                        summary["api_calls"] += 1
                        _log(f"  {game_pk} | fetched weather for {cache_key}")
                    else:
                        _log(f"  {game_pk} | weather fetch failed for {cache_key}", "WARN")

                if weather.get("wind_dir") and wind_out and wind_out not in ("NULL", ""):
                    wind_blowing_out = 1 if weather["wind_dir"].strip().upper() == wind_out.strip().upper() else 0

        output_rows.append({
            "gamePk":              game_pk,
            "venue_id":            venue_id,
            "weather_applicable":  weather_applicable,
            "weather_time":        weather.get("weather_time"),
            "temp_f":              weather.get("temp_f"),
            "wind_mph":            weather.get("wind_mph"),
            "wind_dir":            weather.get("wind_dir"),
            "gust_mph":            weather.get("gust_mph"),
            "precip_in":           weather.get("precip_in"),
            "humidity":            weather.get("humidity"),
            "chance_of_rain":      weather.get("chance_of_rain"),
            "will_it_rain":        weather.get("will_it_rain"),
            "wind_blowing_out":    wind_blowing_out,
        })

    if output_rows:
        pd.DataFrame(output_rows).to_csv(weather_path, index=False)
        _log(f"  WROTE: {weather_path.name} ({len(output_rows)} rows, {summary['api_calls']} API calls)")
        summary["files_written"] += 1


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== fetch_weather RUN {_now()} ===\n")

    summary = {
        "files_written": 0,
        "api_calls":     0,
        "skipped":       0,
        "errors":        0,
    }

    try:
        venue_map = load_venue_map()
        _log(f"Venue map loaded: {len(venue_map)} entries")

        games_files = sorted(GAMES_DIR.glob("*_games.csv"))
        _log(f"Games files found: {len(games_files)}")

        for gf in games_files:
            date_str = gf.stem.replace("_games", "")
            try:
                process_date(date_str, venue_map, summary)
            except Exception as e:
                _log(f"{date_str} FAILED: {e}\n{traceback.format_exc()}", "ERROR")
                summary["errors"] += 1

    except Exception as e:
        _log(f"FATAL: {e}\n{traceback.format_exc()}", "ERROR")
        summary["errors"] += 1

    status = "SUCCESS" if summary["errors"] == 0 else "COMPLETED WITH ERRORS"
    lines = [
        "",
        "=" * 60,
        f"SUMMARY  {_now()}",
        "=" * 60,
        f"  files_written  : {summary['files_written']}",
        f"  api_calls      : {summary['api_calls']}",
        f"  skipped        : {summary['skipped']}",
        f"  errors         : {summary['errors']}",
        "",
        f"STATUS: {status}",
        "=" * 60,
    ]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"fetch_weather complete. {summary['files_written']} files written, {summary['api_calls']} API calls. Status: {status}")


if __name__ == "__main__":
    main()
