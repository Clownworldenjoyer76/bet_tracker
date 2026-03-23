import requests
import os
import json

API_KEY = os.getenv("ODDS_API_KEY")

sports = [
    "basketball_nba",
    "icehockey_nhl"
]

for sport in sports:
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

    params = {
        "apiKey": API_KEY,
        "markets": "h2h,spreads,totals",
        "bookmakers": "draftkings"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Error for {sport}: {response.status_code}")
        print(response.text)
        continue

    data = response.json()

    filename = f"{sport}.json"
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved {filename}")
