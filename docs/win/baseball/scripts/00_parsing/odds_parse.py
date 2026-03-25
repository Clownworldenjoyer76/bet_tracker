import json
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

INPUT_PATH = Path(sys.argv[1])  # can be file OR directory

# ---- TIME CONVERSION (UTC -> EST) ----
def utc_to_est(utc_str):
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    est = dt.astimezone(timezone(timedelta(hours=-5)))
    return est.strftime("%Y-%m-%d"), est.strftime("%H:%M:%S")

# ---- ODDS CONVERSION ----
def decimal_to_american(decimal_odds):
    if decimal_odds is None:
        return None
    if decimal_odds >= 2:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

# ---- PROCESS ONE FILE ----
def process_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)

    output_date = file_path.stem
    output_path = f"docs/win/baseball/sportsbook/{output_date}_MLB.csv"

    rows = []

    for game in data:
        sport = "baseball"
        league = "mlb"

        game_date, game_time = utc_to_est(game["commence_time"])

        away_team = game["away_team"]
        home_team = game["home_team"]

        away_run_line = None
        home_run_line = None
        total = None

        away_rl_dec = None
        home_rl_dec = None
        over_dec = None
        under_dec = None
        away_ml_dec = None
        home_ml_dec = None

        if not game.get("bookmakers"):
            continue

        markets = game["bookmakers"][0].get("markets", [])

        for market in markets:
            key = market["key"]

            if key == "h2h":
                for o in market["outcomes"]:
                    if o["name"] == away_team:
                        away_ml_dec = o["price"]
                    elif o["name"] == home_team:
                        home_ml_dec = o["price"]

            elif key == "spreads":
                for o in market["outcomes"]:
                    if o["name"] == away_team:
                        away_run_line = o["point"]
                        away_rl_dec = o["price"]
                    elif o["name"] == home_team:
                        home_run_line = o["point"]
                        home_rl_dec = o["price"]

            elif key == "totals":
                if market["outcomes"]:
                    total = market["outcomes"][0]["point"]

                for o in market["outcomes"]:
                    if o["name"] == "Over":
                        over_dec = o["price"]
                    elif o["name"] == "Under":
                        under_dec = o["price"]

        # convert to american
        away_rl_amer = decimal_to_american(away_rl_dec)
        home_rl_amer = decimal_to_american(home_rl_dec)
        over_amer = decimal_to_american(over_dec)
        under_amer = decimal_to_american(under_dec)
        away_ml_amer = decimal_to_american(away_ml_dec)
        home_ml_amer = decimal_to_american(home_ml_dec)

        row = [
            sport,
            league,
            game_date,
            game_time,
            home_team,
            away_team,
            away_run_line,
            home_run_line,
            total,
            away_rl_amer,
            home_rl_amer,
            over_amer,
            under_amer,
            away_ml_amer,
            home_ml_amer,
            away_rl_dec,
            home_rl_dec,
            over_dec,
            under_dec,
            away_ml_dec,
            home_ml_dec
        ]

        rows.append(row)

    Path("docs/win/baseball/sportsbook").mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sport","league","game_date","game_time","home_team","away_team",
            "away_run_line","home_run_line","total",
            "away_dk_run_line_american","home_dk_run_line_american",
            "dk_total_over_american","dk_total_under_american",
            "away_dk_moneyline_american","home_dk_moneyline_american",
            "away_dk_run_line_decimal","home_dk_run_line_decimal",
            "dk_total_over_decimal","dk_total_under_decimal",
            "away_dk_moneyline_decimal","home_dk_moneyline_decimal"
        ])
        writer.writerows(rows)

    print(f"Saved {output_path}")

# ---- ENTRY ----
if INPUT_PATH.is_file():
    process_file(INPUT_PATH)
elif INPUT_PATH.is_dir():
    for file in sorted(INPUT_PATH.glob("*.json")):
        process_file(file)
else:
    print("Invalid input path")
