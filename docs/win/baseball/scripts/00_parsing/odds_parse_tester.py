#!/usr/bin/env python3
# docs/win/baseball/scripts/00_intake/odds_parse_tester.py

import sys
import json
import csv
import traceback
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


ERROR_DIR = Path("docs/win/baseball/errors/00_intake/tester")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "odds_parse_tester.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== odds_parse_tester RUN {datetime.now().isoformat()} ===\n")


def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {msg}\n")


# -----------------------
# INPUT HANDLING
# -----------------------

if len(sys.argv) > 1:
    INPUT_PATH = Path(sys.argv[1])
else:
    INPUT_PATH = Path("docs/win/baseball/odds/tester")

if not INPUT_PATH.exists():
    log(f"FATAL ERROR: Input path does not exist: {INPUT_PATH}")
    log("STATUS: FAILED")
    raise FileNotFoundError(f"Input path does not exist: {INPUT_PATH}")


# -----------------------
# TIME CONVERSION
# -----------------------

def utc_to_est(utc_str):
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    est = dt.astimezone(ZoneInfo("America/New_York"))
    return est.strftime("%Y_%m_%d"), est.strftime("%H:%M:%S")


# -----------------------
# ODDS CONVERSION
# -----------------------

def decimal_to_american(decimal_odds):
    if decimal_odds is None:
        return None

    decimal_odds = float(decimal_odds)

    if decimal_odds >= 2:
        return int((decimal_odds - 1) * 100)

    return int(-100 / (decimal_odds - 1))


# -----------------------
# PROCESS ONE FILE
# -----------------------

def process_file(file_path, files_written):
    log(f"Processing {file_path.name}")

    games_parsed = 0
    games_skipped = 0
    games_missing_markets = 0
    games_missing_core_prices = 0

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected list JSON in {file_path}, got {type(data).__name__}")

    grouped_rows = {}

    for game in data:
        game_id = game.get("id")

        sport = "baseball"
        league = "mlb"

        if not game.get("commence_time"):
            games_skipped += 1
            log(f"  SKIPPED missing commence_time: game_id={game_id}")
            continue

        game_date, game_time = utc_to_est(game["commence_time"])

        away_team = game.get("away_team")
        home_team = game.get("home_team")

        if not away_team or not home_team:
            games_skipped += 1
            log(f"  SKIPPED missing team name: game_id={game_id}")
            continue

        away_run_line = home_run_line = total = None
        away_rl_dec = home_rl_dec = over_dec = under_dec = None
        away_ml_dec = home_ml_dec = None

        if not game.get("bookmakers"):
            games_skipped += 1
            log(f"  SKIPPED no bookmakers: game_id={game_id} {away_team} @ {home_team}")
            continue

        markets = game["bookmakers"][0].get("markets", [])

        if not markets:
            games_skipped += 1
            log(f"  SKIPPED no markets: game_id={game_id} {away_team} @ {home_team}")
            continue

        found_keys = set()

        for market in markets:
            key = market.get("key")
            found_keys.add(key)

            outcomes = market.get("outcomes", [])

            if key == "h2h":
                for o in outcomes:
                    if o.get("name") == away_team:
                        away_ml_dec = o.get("price")
                    elif o.get("name") == home_team:
                        home_ml_dec = o.get("price")

            elif key == "spreads":
                for o in outcomes:
                    if o.get("name") == away_team:
                        away_run_line = o.get("point")
                        away_rl_dec = o.get("price")
                    elif o.get("name") == home_team:
                        home_run_line = o.get("point")
                        home_rl_dec = o.get("price")

            elif key == "totals":
                for o in outcomes:
                    if o.get("name") == "Over":
                        total = o.get("point")
                        over_dec = o.get("price")
                    elif o.get("name") == "Under":
                        if total is None:
                            total = o.get("point")
                        under_dec = o.get("price")

        missing_market_keys = {"h2h", "spreads", "totals"} - found_keys

        if missing_market_keys:
            games_missing_markets += 1
            log(
                "  WARNING missing markets "
                f"{sorted(missing_market_keys)}: game_id={game_id} {away_team} @ {home_team}"
            )

        core_values = {
            "away_ml_dec": away_ml_dec,
            "home_ml_dec": home_ml_dec,
            "away_run_line": away_run_line,
            "home_run_line": home_run_line,
            "total": total,
            "away_rl_dec": away_rl_dec,
            "home_rl_dec": home_rl_dec,
            "over_dec": over_dec,
            "under_dec": under_dec,
        }

        missing_core_values = [
            key for key, value in core_values.items()
            if value is None or value == ""
        ]

        if missing_core_values:
            games_missing_core_prices += 1
            log(
                "  WARNING missing core values "
                f"{missing_core_values}: game_id={game_id} {away_team} @ {home_team}"
            )

        row = [
            game_id,
            sport,
            league,
            game_date,
            game_time,
            home_team,
            away_team,
            away_run_line,
            home_run_line,
            total,
            decimal_to_american(away_rl_dec),
            decimal_to_american(home_rl_dec),
            decimal_to_american(over_dec),
            decimal_to_american(under_dec),
            decimal_to_american(away_ml_dec),
            decimal_to_american(home_ml_dec),
            away_rl_dec,
            home_rl_dec,
            over_dec,
            under_dec,
            away_ml_dec,
            home_ml_dec,
        ]

        grouped_rows.setdefault(game_date, []).append(row)
        games_parsed += 1

    base_output_dir = Path("docs/win/baseball/00_intake/sportsbook/tester")
    base_output_dir.mkdir(parents=True, exist_ok=True)

    for game_date, rows in grouped_rows.items():
        output_path = base_output_dir / f"{game_date}_MLB.csv"

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "game_id",
                "sport",
                "league",
                "game_date",
                "game_time",
                "home_team",
                "away_team",
                "away_run_line",
                "home_run_line",
                "total",
                "away_dk_run_line_american",
                "home_dk_run_line_american",
                "dk_total_over_american",
                "dk_total_under_american",
                "away_dk_moneyline_american",
                "home_dk_moneyline_american",
                "away_dk_run_line_decimal",
                "home_dk_run_line_decimal",
                "dk_total_over_decimal",
                "dk_total_under_decimal",
                "away_dk_moneyline_decimal",
                "home_dk_moneyline_decimal",
            ])
            writer.writerows(rows)

        files_written.append((str(output_path), len(rows)))
        log(f"  WROTE {output_path} ({len(rows)} games)")

    log(
        f"  games_parsed={games_parsed}, "
        f"games_skipped={games_skipped}, "
        f"games_missing_markets={games_missing_markets}, "
        f"games_missing_core_prices={games_missing_core_prices}"
    )


# -----------------------
# ENTRY
# -----------------------

def main():
    files_written = []

    try:
        if INPUT_PATH.is_file():
            process_file(INPUT_PATH, files_written)

        elif INPUT_PATH.is_dir():
            files = list(INPUT_PATH.glob("*.json"))

            if not files:
                log(f"No JSON files found in {INPUT_PATH}")
                log("STATUS: SUCCESS (nothing to do)")
                return

            for file in sorted(files):
                process_file(file, files_written)

        else:
            raise ValueError(f"Invalid input path: {INPUT_PATH}")

        log("--- SUMMARY ---")
        log(f"Files written: {len(files_written)}")

        for path, count in files_written:
            log(f"  FILE: {path} ({count} games)")

        log("STATUS: SUCCESS")

    except Exception as e:
        log(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
        log("STATUS: FAILED")
        raise


if __name__ == "__main__":
    main()
