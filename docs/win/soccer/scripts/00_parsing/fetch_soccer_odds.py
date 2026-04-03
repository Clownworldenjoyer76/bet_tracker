import requests
import os
import csv
from collections import defaultdict

API_KEY = os.getenv("CLOUD_API")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

BASE_PATH = "docs/win/soccer/00_intake/sportsbook"
os.makedirs(BASE_PATH, exist_ok=True)

LEAGUES = [
    "soccer-england-premier-league",
    "soccer-spain-laliga",
    "soccer-france-ligue-1",
    "soccer-germany-bundesliga",
    "soccer-italy-serie-a",
    "soccer-usa-major-league-soccer"
]

def get_json(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def interpolate(lines, target):
    if target in lines:
        return lines[target]

    lower = max((k for k in lines if k < target), default=None)
    upper = min((k for k in lines if k > target), default=None)

    if lower and upper:
        return (lines[lower] + lines[upper]) / 2

    return None

output = []

for league in LEAGUES:

    comp_url = f"https://sports-api.cloudbet.com/pub/v2/odds/competitions/{league}"
    comp = get_json(comp_url)

    for event in comp.get("events", []):

        if not event.get("home") or not event.get("away"):
            continue

        event_id = event["id"]

        game = get_json(f"https://sports-api.cloudbet.com/pub/v2/odds/events/{event_id}")

        markets = game.get("markets")
        if not markets:
            continue

        start = game.get("startTime") or game.get("cutoffTime")
        if not start:
            continue

        date, time = start.replace("Z", "").split("T")

        row = {
            "league": league,
            "market": "combined",
            "game_id": game["id"],
            "match_date": date,
            "match_time": time,
            "home_team": game["home"]["name"],
            "away_team": game["away"]["name"],

            "dk_home_decimal": None,
            "dk_draw_decimal": None,
            "dk_away_decimal": None,

            "dk_over25_decimal": None,
            "dk_under25_decimal": None,
            "dk_over35_decimal": None,
            "dk_under35_decimal": None,

            "btts_yes": None,
            "btts_no": None
        }

        # MATCH ODDS
        mo = markets.get("soccer.match_odds")
        if mo:
            for sub in mo["submarkets"].values():
                for s in sub["selections"]:
                    if s["outcome"] == "home":
                        row["dk_home_decimal"] = s["price"]
                    elif s["outcome"] == "draw":
                        row["dk_draw_decimal"] = s["price"]
                    elif s["outcome"] == "away":
                        row["dk_away_decimal"] = s["price"]

        # TOTALS (INTERPOLATED)
        over_lines = {}
        under_lines = {}

        tg = markets.get("soccer.total_goals")
        if tg:
            for sub in tg["submarkets"].values():
                for s in sub["selections"]:
                    params = s.get("params", "")
                    if "total=" in params:
                        try:
                            line = float(params.split("=")[1])
                        except:
                            continue

                        if s["outcome"] == "over":
                            over_lines[line] = s["price"]
                        elif s["outcome"] == "under":
                            under_lines[line] = s["price"]

        row["dk_over25_decimal"] = interpolate(over_lines, 2.5)
        row["dk_under25_decimal"] = interpolate(under_lines, 2.5)

        row["dk_over35_decimal"] = interpolate(over_lines, 3.5)
        row["dk_under35_decimal"] = interpolate(under_lines, 3.5)

        # BTTS
        btts = markets.get("soccer.both_teams_to_score")
        if btts:
            for sub in btts["submarkets"].values():
                for s in sub["selections"]:
                    if s["outcome"] == "yes":
                        row["btts_yes"] = s["price"]
                    elif s["outcome"] == "no":
                        row["btts_no"] = s["price"]

        if row["dk_home_decimal"] or row["dk_over25_decimal"] or row["btts_yes"]:
            output.append(row)

# --- GROUP BY DATE ---
grouped = defaultdict(list)
for row in output:
    grouped[row["match_date"]].append(row)

# --- WRITE CSV FILES ---
for date, rows in grouped.items():
    path = os.path.join(BASE_PATH, f"{date}_soccer.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

print(f"Total rows: {len(output)}")
