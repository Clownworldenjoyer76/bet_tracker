import requests
import os
import json
from pathlib import Path

API_KEY = os.getenv("ODDS_API_KEY")

targets = {
    "basketball_nba": "docs/win/basketball/odds/nba.json",
    "icehockey_nhl": "docs/win/hockey/odds/nhl.json"
}

for sport, path in targets.items():
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

    params = {
        "apiKey": API_KEY,
        "markets": "h2h,spreads,totals",
        "bookmakers": "draftkings"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"{sport} error: {response.status_code}")
        print(response.text)
        continue

    data = response.json()

    # ensure directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved {path}")
