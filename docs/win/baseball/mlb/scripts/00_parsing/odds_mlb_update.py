#!/usr/bin/env python3
# docs/win/baseball/mlb/scripts/00_parsing/odds_mlb_update.py

import json
import os
from pathlib import Path
from datetime import datetime, timezone

import requests


API_KEY = os.getenv("API_ODDS")

if not API_KEY:
    raise RuntimeError("API_ODDS environment variable is not set")


BASE_URL = "https://api.odds-api.io/v3"

SPORT = "baseball"
LEAGUE = "usa-mlb"
BOOKMAKER = "DraftKings"

now_utc = datetime.now(timezone.utc)
today = now_utc.strftime("%Y_%m_%d")
stamp = now_utc.strftime("%Y_%m_%d_%H%M")

ODDS_DIR = Path("docs/win/baseball/mlb/odds")
ORIGINAL_PATH = ODDS_DIR / f"{today}.json"
UPDATES_DIR = ODDS_DIR / "updates"
LATEST_DIR = ODDS_DIR / "latest"

UPDATE_PATH = UPDATES_DIR / f"{stamp}.json"
LATEST_PATH = LATEST_DIR / f"{today}.json"


def get_json(endpoint, params):
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        timeout=30,
    )

    if response.status_code != 200:
        print(f"{endpoint} error: {response.status_code}")
        print(response.text)
        raise SystemExit(1)

    return response.json()


def fetch_events():
    events = []
    skip = 0
    limit = 100

    while True:
        batch = get_json(
            "/events",
            {
                "apiKey": API_KEY,
                "sport": SPORT,
                "league": LEAGUE,
                "status": "pending,live",
                "bookmaker": BOOKMAKER,
                "limit": limit,
                "skip": skip,
            },
        )

        if not isinstance(batch, list):
            print("Unexpected /events response:")
            print(json.dumps(batch, indent=2))
            raise SystemExit(1)

        events.extend(batch)

        if len(batch) < limit:
            break

        skip += limit

    return events


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def fetch_odds(event_ids):
    odds = []

    for batch_ids in chunks(event_ids, 10):
        batch = get_json(
            "/odds/multi",
            {
                "apiKey": API_KEY,
                "eventIds": ",".join(str(event_id) for event_id in batch_ids),
                "bookmakers": BOOKMAKER,
            },
        )

        if not isinstance(batch, list):
            print("Unexpected /odds/multi response:")
            print(json.dumps(batch, indent=2))
            raise SystemExit(1)

        odds.extend(batch)

    return odds


def to_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def market_key(name):
    normalized = str(name or "").strip().lower()

    if normalized == "ml":
        return "h2h"

    if normalized in {"spread", "spreads", "asian handicap", "handicap"}:
        return "spreads"

    if normalized in {"totals", "total", "over/under", "over under"}:
        return "totals"

    return None


def convert_market(event, market):
    key = market_key(market.get("name"))

    if key not in {"h2h", "spreads", "totals"}:
        return None

    converted = {
        "key": key,
        "last_update": market.get("updatedAt"),
        "outcomes": [],
    }

    odds_rows = market.get("odds") or []

    for row in odds_rows:
        if key == "h2h":
            home_price = to_float(row.get("home"))
            away_price = to_float(row.get("away"))

            if home_price is not None:
                converted["outcomes"].append(
                    {
                        "name": event.get("home"),
                        "price": home_price,
                    }
                )

            if away_price is not None:
                converted["outcomes"].append(
                    {
                        "name": event.get("away"),
                        "price": away_price,
                    }
                )

        elif key == "spreads":
            point = to_float(row.get("hdp"))
            home_price = to_float(row.get("home"))
            away_price = to_float(row.get("away"))

            if home_price is not None:
                converted["outcomes"].append(
                    {
                        "name": event.get("home"),
                        "price": home_price,
                        "point": point,
                    }
                )

            if away_price is not None:
                converted["outcomes"].append(
                    {
                        "name": event.get("away"),
                        "price": away_price,
                        "point": -point if point is not None else None,
                    }
                )

        elif key == "totals":
            point = to_float(row.get("hdp"))
            over_price = to_float(row.get("over"))
            under_price = to_float(row.get("under"))

            if over_price is not None:
                converted["outcomes"].append(
                    {
                        "name": "Over",
                        "price": over_price,
                        "point": point,
                    }
                )

            if under_price is not None:
                converted["outcomes"].append(
                    {
                        "name": "Under",
                        "price": under_price,
                        "point": point,
                    }
                )

    if not converted["outcomes"]:
        return None

    return converted


def convert_event(event):
    bookmakers = event.get("bookmakers") or {}
    bookmaker_markets = bookmakers.get(BOOKMAKER, [])

    converted_markets = []

    for market in bookmaker_markets:
        converted_market = convert_market(event, market)
        if converted_market:
            converted_markets.append(converted_market)

    if not converted_markets:
        return None

    last_update_values = [
        market.get("last_update")
        for market in converted_markets
        if market.get("last_update")
    ]

    bookmaker = {
        "key": "draftkings",
        "title": BOOKMAKER,
        "last_update": max(last_update_values) if last_update_values else None,
        "markets": converted_markets,
    }

    return {
        "id": str(event.get("id")),
        "sport_key": "baseball_mlb",
        "sport_title": "MLB",
        "commence_time": event.get("date"),
        "home_team": event.get("home"),
        "away_team": event.get("away"),
        "bookmakers": [bookmaker],
    }


def read_json_list(path):
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except json.JSONDecodeError:
        print(f"Invalid JSON in existing file: {path}")
        raise SystemExit(1)

    if not isinstance(loaded, list):
        print(f"Expected JSON list in existing file: {path}")
        raise SystemExit(1)

    return loaded


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    temp_path.replace(path)


def event_id(event):
    value = event.get("id")

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def choose_latest_seed():
    if LATEST_PATH.exists():
        return LATEST_PATH, read_json_list(LATEST_PATH)

    if ORIGINAL_PATH.exists():
        return ORIGINAL_PATH, read_json_list(ORIGINAL_PATH)

    return None, []


def merge_latest(existing_events, pulled_events):
    existing_by_id = {}
    existing_without_id = []
    existing_order = []

    for event in existing_events:
        if not isinstance(event, dict):
            existing_without_id.append(event)
            continue

        eid = event_id(event)

        if eid is None:
            existing_without_id.append(event)
            continue

        if eid not in existing_by_id:
            existing_order.append(eid)

        existing_by_id[eid] = event

    pulled_by_id = {}
    pulled_order = []
    pulled_without_id = []

    for event in pulled_events:
        if not isinstance(event, dict):
            pulled_without_id.append(event)
            continue

        eid = event_id(event)

        if eid is None:
            pulled_without_id.append(event)
            continue

        if eid not in pulled_by_id:
            pulled_order.append(eid)

        pulled_by_id[eid] = event

    updated_count = 0
    added_count = 0

    for eid in pulled_order:
        if eid in existing_by_id:
            updated_count += 1
        else:
            existing_order.append(eid)
            added_count += 1

        existing_by_id[eid] = pulled_by_id[eid]

    preserved_count = 0

    for eid in existing_order:
        if eid not in pulled_by_id:
            preserved_count += 1

    merged = []

    for eid in existing_order:
        merged.append(existing_by_id[eid])

    merged.extend(existing_without_id)
    merged.extend(pulled_without_id)

    return merged, updated_count, added_count, preserved_count


events = fetch_events()

if not events:
    print("No MLB events found with DraftKings odds.")
    pulled_data = []
else:
    event_ids = [event["id"] for event in events if event.get("id") is not None]
    raw_odds = fetch_odds(event_ids)

    pulled_data = []

    for event in raw_odds:
        converted = convert_event(event)
        if converted:
            pulled_data.append(converted)

seed_path, existing_latest_data = choose_latest_seed()
latest_data, updated_count, added_count, preserved_count = merge_latest(
    existing_latest_data,
    pulled_data,
)

write_json(UPDATE_PATH, pulled_data)
write_json(LATEST_PATH, latest_data)

print(f"Saved update pull: {UPDATE_PATH}")
print(f"Saved cumulative latest: {LATEST_PATH}")

if seed_path:
    print(f"Latest seed source: {seed_path}")
else:
    print("Latest seed source: none")

print(f"Events found: {len(events)}")
print(f"Events with converted DraftKings odds this pull: {len(pulled_data)}")
print(f"Existing latest seed count: {len(existing_latest_data)}")
print(f"Updated existing events in latest: {updated_count}")
print(f"Added new events to latest: {added_count}")
print(f"Preserved events missing from this pull: {preserved_count}")
print(f"Final latest event count: {len(latest_data)}")
