#!/usr/bin/env python3
# docs/win/baseball/scripts/00_intake/enrich_game_context.py
#
# Runs daily after scrape_mlb_raw.py.
# Reads {date}_mlb_raw.csv and joins all contextual data to produce
# {date}_game_context.csv at docs/win/baseball/00_intake/mlb_raw/

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
MLBraw_DIR    = BASE_DIR / "00_intake/mlb_raw"
MAPS_DIR      = BASE_DIR / "maps"
DATA_DIR      = BASE_DIR / "data"
WEATHER_CACHE = DATA_DIR / "weather"
ERROR_DIR     = BASE_DIR / "errors/00_intake"

WEATHER_CACHE.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "enrich_game_context.txt"

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
# LOAD MAPS (once at startup)
# ─────────────────────────────────────────────

def load_maps():
    venue_df = pd.read_csv(
        MAPS_DIR / "mlb_venue_ids.csv",
        dtype={"venue_id": str},
        encoding="utf-8-sig"
    )
    venue_df["venue_id"] = venue_df["venue_id"].str.strip()
    venue_map = venue_df.set_index("venue_id").to_dict("index")

    pitcher_df = pd.read_csv(
        MAPS_DIR / "mlb_pitcher_ids.csv",
        dtype={"pitcher_id": str},
        encoding="utf-8-sig"
    )
    pitcher_df["pitcher_id"] = pitcher_df["pitcher_id"].str.strip()
    pitcher_map = pitcher_df.set_index("pitcher_id")["pitch_hand_code"].to_dict()

    batter_df = pd.read_csv(
        MAPS_DIR / "mlb_batter_ids.csv",
        dtype={"batter_id": str},
        encoding="utf-8-sig"
    )
    batter_df["batter_id"] = batter_df["batter_id"].str.strip()
    batter_map = batter_df.set_index("batter_id").to_dict("index")

    return venue_map, pitcher_map, batter_map


# ─────────────────────────────────────────────
# LOAD STATCAST DATA (once at startup)
# ─────────────────────────────────────────────

BATTING_COLS  = ["player_id", "pa", "xwoba", "barrel_pct", "hard_hit_pct",
                 "k_pct", "bb_pct", "exit_velo", "sample_flag"]
PITCHING_COLS = ["player_id", "pa", "xwoba", "k_pct", "bb_pct",
                 "barrel_pct", "whiff_pct", "exit_velo", "sample_flag"]

# Oldest to newest — newer years overwrite older on duplicate player_id
STATCAST_PRIORITY = ["2022", "2023", "2024", "2025", "2026"]


def _load_statcast(directory: Path, cols: list, id_col: str = "player_id") -> dict:
    """
    Load clean Statcast files in priority order: 2026 > 2025 > 2024 > 2023 > 2022.
    Returns dict keyed by player_id -> row dict. Most recent year wins.
    """
    merged = {}
    for yr in STATCAST_PRIORITY:
        files = list(directory.glob(f"*{yr}*_clean.csv"))
        if not files:
            continue
        df = pd.read_csv(files[0], dtype={id_col: str})
        df[id_col] = df[id_col].str.strip()
        available = [c for c in cols if c in df.columns]
        merged.update(df[available].set_index(id_col).to_dict("index"))
    return merged


def load_statcast():
    batting  = _load_statcast(DATA_DIR / "batting",  BATTING_COLS)
    pitching = _load_statcast(DATA_DIR / "pitching", PITCHING_COLS)

    # Fielding: oldest to newest, newest wins per player
    fielding = {}
    for yr in STATCAST_PRIORITY:
        for f in sorted((DATA_DIR / "fielding").glob(f"*{yr}*_clean.csv")):
            df = pd.read_csv(f, dtype={"id": str})
            df["id"] = df["id"].str.strip()
            for _, row in df.iterrows():
                fielding[row["id"]] = row.to_dict()

    # Baserunning: oldest to newest, newest wins per player
    baserunning = {}
    for yr in STATCAST_PRIORITY:
        for f in sorted((DATA_DIR / "baserunning").glob(f"*{yr}*_clean.csv")):
            df = pd.read_csv(f, dtype={"player_id": str})
            df["player_id"] = df["player_id"].str.strip()
            for _, row in df.iterrows():
                baserunning[row["player_id"]] = row.to_dict()

    return batting, pitching, fielding, baserunning


# ─────────────────────────────────────────────
# LOAD PARK FACTORS (once at startup)
# ─────────────────────────────────────────────

def load_park_factors() -> list:
    """Returns list of dicts from all park_B_*_clean.csv files."""
    rows = []
    for f in sorted((DATA_DIR / "park_factors").glob("park_B_*_clean.csv")):
        df = pd.read_csv(f, dtype={"venue_id": str})
        df["venue_id"] = df["venue_id"].str.strip()
        rows.extend(df.to_dict("records"))
    return rows


def get_park_condition(roof_type: str, day_night: str) -> str:
    rt = (roof_type or "").strip().lower()
    dn = (day_night or "").strip().lower()
    if rt in ("dome", "indoor"):
        return "roof_closed"
    if rt == "retractable":
        return "day" if dn == "day" else "night"
    # open / outdoor
    return "open_air"


def lookup_park(park_rows: list, venue_id: str, condition: str) -> dict:
    for row in park_rows:
        if (str(row.get("venue_id", "")).strip() == str(venue_id) and
                str(row.get("condition", "")).strip().lower() == condition.lower()):
            return row
    return {}


# ─────────────────────────────────────────────
# WEATHER
# ─────────────────────────────────────────────

def _game_local_hour(game_time_utc: str, tz_id: str) -> tuple:
    """Convert UTC game_time string to local date and hour."""
    try:
        dt_utc = datetime.strptime(game_time_utc.strip(), "%Y-%m-%dT%H:%M:%SZ")
        dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
        dt_loc = dt_utc.astimezone(ZoneInfo(tz_id))
        return dt_loc.strftime("%Y-%m-%d"), str(dt_loc.hour)
    except Exception as e:
        _log(f"Timezone conversion failed for {game_time_utc} / {tz_id}: {e}", "WARN")
        return None, None


def fetch_weather(lat: str, lon: str, game_time_utc: str, tz_id: str,
                  cache_df: pd.DataFrame) -> dict:
    """Fetch weather from API or cache."""
    local_date, local_hour = _game_local_hour(game_time_utc, tz_id)
    if not local_date or not local_hour:
        return {}

    cache_key = f"{lat}_{lon}_{local_date}_{local_hour}"

    if not cache_df.empty and cache_key in cache_df["cache_key"].values:
        _log(f"  Weather cache hit: {cache_key}")
        return cache_df[cache_df["cache_key"] == cache_key].iloc[0].to_dict()

    if not WEATHER_API_KEY:
        _log("WEATHER_API not set — skipping weather fetch", "WARN")
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
            "cache_key":      cache_key,
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
# STATCAST LOOKUP HELPERS
# ─────────────────────────────────────────────

def get_pitcher_stats(pitcher_id: str, pitching: dict) -> dict:
    pid = str(pitcher_id).strip()
    row = pitching.get(pid)
    if not row:
        _log(f"  Pitcher {pid} not found in any Statcast file", "WARN")
        return {}
    return row


BATTER_AVG_COLS = ["xwoba", "barrel_pct", "hard_hit_pct", "k_pct", "bb_pct", "exit_velo"]


def aggregate_lineup(batter_ids: list, batting: dict, fielding: dict,
                     baserunning: dict, batter_map: dict, side: str) -> dict:
    """Aggregate stats for a 9-batter lineup."""
    avg_accum       = {c: [] for c in BATTER_AVG_COLS}
    frv_sum         = 0.0
    brv_sum         = 0.0
    low_sample      = 0
    catcher_framing = None

    for i, bid in enumerate(batter_ids):
        bid   = str(bid).strip()
        label = f"{side}_bat_{i+1}"

        # Batting Statcast
        bstats = batting.get(bid)
        if not bstats:
            _log(f"  Batter {bid} ({label}) not found in any Statcast file", "WARN")
        else:
            for col in BATTER_AVG_COLS:
                val = bstats.get(col)
                if val is not None:
                    try:
                        avg_accum[col].append(float(val))
                    except (ValueError, TypeError):
                        pass
            if bstats.get("sample_flag") == "low":
                low_sample += 1

        # Fielding — total_runs sum (exclude framing)
        fstats = fielding.get(bid, {})
        try:
            frv_sum += float(fstats.get("total_runs", 0) or 0)
        except (ValueError, TypeError):
            pass

        # Catcher framing — position code 2 = catcher
        bmap_row = batter_map.get(bid, {})
        if str(bmap_row.get("primary_position_code", "")).strip() == "2":
            try:
                catcher_framing = float(fstats.get("framing_runs", 0) or 0)
            except (ValueError, TypeError):
                catcher_framing = None

        # Baserunning
        brstats = baserunning.get(bid, {})
        try:
            brv_sum += float(brstats.get("runner_runs_tot", 0) or 0)
        except (ValueError, TypeError):
            pass

    result = {}
    for col in BATTER_AVG_COLS:
        vals = avg_accum[col]
        result[f"{side}_lineup_{col}"] = (sum(vals) / len(vals)) if vals else None

    result[f"{side}_lineup_frv"]       = frv_sum
    result[f"{side}_lineup_brv"]       = brv_sum
    result[f"{side}_catcher_framing"]  = catcher_framing
    result[f"{side}_low_sample_count"] = low_sample
    return result


# ─────────────────────────────────────────────
# PROCESS ONE DATE
# ─────────────────────────────────────────────

def process_date(date_str: str, venue_map: dict, pitcher_map: dict, batter_map: dict,
                 batting: dict, pitching: dict, fielding: dict, baserunning: dict,
                 park_rows: list, summary: dict) -> None:

    raw_path = MLBraw_DIR / f"{date_str}_mlb_raw.csv"
    if not raw_path.exists():
        _log(f"mlb_raw file not found: {raw_path}", "WARN")
        summary["missing_raw"] += 1
        return

    df = pd.read_csv(raw_path, dtype=str)
    _log(f"--- {date_str} | {len(df)} games")

    weather_cache_path = WEATHER_CACHE / f"{date_str}_weather.csv"
    cache_df = pd.read_csv(weather_cache_path, dtype=str) if weather_cache_path.exists() else pd.DataFrame()
    if not cache_df.empty:
        _log(f"  Weather cache loaded: {len(cache_df)} entries")

    new_weather_rows = []
    output_rows      = []

    for _, row in df.iterrows():
        game_pk   = row.get("gamePk", "")
        game_date = row.get("game_date", "")
        game_time = row.get("game_time", "")
        venue_id  = str(row.get("venue_id", "")).strip()
        day_night = str(row.get("day_night", "")).strip().lower()
        home_tid  = str(row.get("home_team_id", "")).strip()
        away_tid  = str(row.get("away_team_id", "")).strip()
        home_pid  = str(row.get("home_pitcher_id", "")).strip()
        away_pid  = str(row.get("away_pitcher_id", "")).strip()

        vinfo     = venue_map.get(venue_id, {})
        roof_type = vinfo.get("roof_type", "")
        turf_type = vinfo.get("turf_type", "")
        lat       = str(vinfo.get("latitude", ""))
        lon       = str(vinfo.get("longitude", ""))
        tz_id     = vinfo.get("time_zone_id", "America/New_York")
        wind_out  = vinfo.get("wind_out_direction", "")

        home_hand = pitcher_map.get(home_pid, None)
        away_hand = pitcher_map.get(away_pid, None)

        hpstats = get_pitcher_stats(home_pid, pitching)
        apstats = get_pitcher_stats(away_pid, pitching)

        home_bats = [row.get(f"home_bat_{i}_id", "") for i in range(1, 10)]
        away_bats = [row.get(f"away_bat_{i}_id", "") for i in range(1, 10)]

        home_agg = aggregate_lineup(home_bats, batting, fielding, baserunning, batter_map, "home")
        away_agg = aggregate_lineup(away_bats, batting, fielding, baserunning, batter_map, "away")

        condition = get_park_condition(roof_type, day_night)
        park_row  = lookup_park(park_rows, venue_id, condition)
        if not park_row:
            _log(f"  Park factor not found: venue={venue_id} condition={condition}", "WARN")

        rt_lower           = roof_type.strip().lower()
        weather_applicable = 0 if rt_lower in ("dome", "indoor") else 1
        weather            = {}
        wind_blowing_out   = None

        if weather_applicable and lat and lon and game_time:
            weather = fetch_weather(lat, lon, game_time, tz_id, cache_df)
            if weather and weather not in new_weather_rows:
                new_weather_rows.append(weather)
            if weather.get("wind_dir") and wind_out and wind_out not in ("NULL", ""):
                wind_blowing_out = 1 if weather["wind_dir"].strip().upper() == wind_out.strip().upper() else 0

        summary["weather_calls"] += (1 if weather and "weather_time" in weather else 0)

        output_rows.append({
            "game_date":             game_date,
            "gamePk":                game_pk,
            "home_team_id":          home_tid,
            "away_team_id":          away_tid,
            "venue_id":              venue_id,
            "roof_type":             roof_type,
            "turf_type":             turf_type,
            "home_pitcher_id":       home_pid,
            "away_pitcher_id":       away_pid,
            "home_pitcher_hand":     home_hand,
            "away_pitcher_hand":     away_hand,
            "home_sp_xwoba":         hpstats.get("xwoba"),
            "away_sp_xwoba":         apstats.get("xwoba"),
            "home_sp_k_pct":         hpstats.get("k_pct"),
            "away_sp_k_pct":         apstats.get("k_pct"),
            "home_sp_bb_pct":        hpstats.get("bb_pct"),
            "away_sp_bb_pct":        apstats.get("bb_pct"),
            "home_sp_barrel_pct":    hpstats.get("barrel_pct"),
            "away_sp_barrel_pct":    apstats.get("barrel_pct"),
            "home_sp_whiff_pct":     hpstats.get("whiff_pct"),
            "away_sp_whiff_pct":     apstats.get("whiff_pct"),
            "home_sp_sample_flag":   hpstats.get("sample_flag"),
            "away_sp_sample_flag":   apstats.get("sample_flag"),
            **home_agg,
            **away_agg,
            "park_factor":           park_row.get("Park Factor"),
            "park_wOBAcon":          park_row.get("wOBAcon"),
            "park_xwOBAcon":         park_row.get("xwOBAcon"),
            "park_HR":               park_row.get("HR"),
            "park_R":                park_row.get("R"),
            "weather_applicable":    weather_applicable,
            "weather_time":          weather.get("weather_time"),
            "temp_f":                weather.get("temp_f"),
            "wind_mph":              weather.get("wind_mph"),
            "wind_dir":              weather.get("wind_dir"),
            "gust_mph":              weather.get("gust_mph"),
            "precip_in":             weather.get("precip_in"),
            "humidity":              weather.get("humidity"),
            "chance_of_rain":        weather.get("chance_of_rain"),
            "will_it_rain":          weather.get("will_it_rain"),
            "wind_blowing_out":      wind_blowing_out,
        })

    if output_rows:
        out_path = MLBraw_DIR / f"{date_str}_game_context.csv"
        pd.DataFrame(output_rows).to_csv(out_path, index=False)
        _log(f"  WROTE: {out_path.name} ({len(output_rows)} rows)")
        summary["files_written"] += 1
        summary["rows_written"]  += len(output_rows)

    if new_weather_rows:
        new_df   = pd.DataFrame(new_weather_rows)
        combined = pd.concat([cache_df, new_df]).drop_duplicates(subset=["cache_key"]) if not cache_df.empty else new_df
        combined.to_csv(weather_cache_path, index=False)
        _log(f"  Weather cache updated: {len(combined)} entries -> {weather_cache_path.name}")
        summary["cache_writes"] += 1


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== enrich_game_context RUN {_now()} ===\n")

    summary = {
        "files_written": 0,
        "rows_written":  0,
        "missing_raw":   0,
        "weather_calls": 0,
        "cache_writes":  0,
        "errors":        0,
    }

    try:
        _log("Loading maps...")
        venue_map, pitcher_map, batter_map = load_maps()
        _log(f"  venue_map: {len(venue_map)} | pitcher_map: {len(pitcher_map)} | batter_map: {len(batter_map)}")

        _log("Loading Statcast data...")
        batting, pitching, fielding, baserunning = load_statcast()
        _log(f"  batting: {len(batting)} | pitching: {len(pitching)} | fielding: {len(fielding)} | baserunning: {len(baserunning)}")

        _log("Loading park factors...")
        park_rows = load_park_factors()
        _log(f"  park_rows: {len(park_rows)}")

        raw_files = sorted(MLBraw_DIR.glob("*_mlb_raw.csv"))
        _log(f"mlb_raw files found: {len(raw_files)}")

        for rf in raw_files:
            date_str = rf.stem.replace("_mlb_raw", "")
            try:
                process_date(date_str, venue_map, pitcher_map, batter_map,
                             batting, pitching, fielding, baserunning,
                             park_rows, summary)
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
        f"  rows_written   : {summary['rows_written']}",
        f"  missing_raw    : {summary['missing_raw']}",
        f"  weather_calls  : {summary['weather_calls']}",
        f"  cache_writes   : {summary['cache_writes']}",
        f"  errors         : {summary['errors']}",
        "",
        f"STATUS: {status}",
        "=" * 60,
    ]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"enrich_game_context complete. {summary['files_written']} files written. Status: {status}")


if __name__ == "__main__":
    main()
