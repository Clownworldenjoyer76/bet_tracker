#docs/win/baseball/mlb/scripts/00_parsing/mlb_odds_pull.py

import requests
import os
import json
from pathlib import Path
from datetime import datetime, timezone


API_KEY = os.getenv("API_ODDS")

if not API_KEY:
    raise RuntimeError("API_ODDS environment variable is not set")


BASE_URL = "https://api.odds-api.io/v3"

SPORT = "baseball"
LEAGUE = "usa-mlb"

PRIMARY_BOOKMAKER = "DraftKings"
FALLBACK_BOOKMAKER = "FanDuel"
BOOKMAKERS = [PRIMARY_BOOKMAKER, FALLBACK_BOOKMAKER]

today = datetime.now(timezone.utc).strftime("%Y_%m_%d")
path = f"docs/win/baseball/mlb/odds/{today}.json"


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


def fetch_events_for_bookmaker(bookmaker):
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
                "bookmaker": bookmaker,
                "limit": limit,
                "skip": skip,
            },
        )

        if not isinstance(batch, list):
            print(f"Unexpected /events response for {bookmaker}:")
            print(json.dumps(batch, indent=2))
            raise SystemExit(1)

        events.extend(batch)

        if len(batch) < limit:
            break

        skip += limit

    return events


def fetch_events():
    by_id = {}
    counts = {}

    for bookmaker in BOOKMAKERS:
        events = fetch_events_for_bookmaker(bookmaker)
        counts[bookmaker] = len(events)

        for event in events:
            event_id = event.get("id")
            if event_id is None:
                continue

            event_id = str(event_id)

            if event_id not in by_id:
                by_id[event_id] = event

            if bookmaker == PRIMARY_BOOKMAKER:
                by_id[event_id] = event

    return list(by_id.values()), counts


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def fetch_odds_for_bookmaker(event_ids, bookmaker):
    odds = []

    for batch_ids in chunks(event_ids, 10):
        batch = get_json(
            "/odds/multi",
            {
                "apiKey": API_KEY,
                "eventIds": ",".join(str(event_id) for event_id in batch_ids),
                "bookmakers": bookmaker,
            },
        )

        if not isinstance(batch, list):
            print(f"Unexpected /odds/multi response for {bookmaker}:")
            print(json.dumps(batch, indent=2))
            raise SystemExit(1)

        odds.extend(batch)

    return odds


def fetch_odds(event_ids):
    by_id = {}

    for bookmaker in BOOKMAKERS:
        bookmaker_odds = fetch_odds_for_bookmaker(event_ids, bookmaker)

        for event in bookmaker_odds:
            event_id = event.get("id")
            if event_id is None:
                continue

            event_id = str(event_id)

            if event_id not in by_id:
                by_id[event_id] = {}

            by_id[event_id][bookmaker] = event

    return by_id


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


def get_bookmaker_markets(event, bookmaker):
    bookmakers = event.get("bookmakers") or {}

    if isinstance(bookmakers, dict):
        return bookmakers.get(bookmaker, []) or []

    if isinstance(bookmakers, list):
        for item in bookmakers:
            title = str(item.get("title") or item.get("key") or "").strip().lower()
            if title == bookmaker.lower():
                return item.get("markets") or []

    return []


def convert_market(event, market):
    key = market_key(market.get("name") or market.get("key"))

    if key not in {"h2h", "spreads", "totals"}:
        return None

    converted = {
        "key": key,
        "last_update": market.get("updatedAt") or market.get("last_update"),
        "outcomes": [],
    }

    odds_rows = market.get("odds") or []

    if odds_rows:
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

    else:
        outcomes = market.get("outcomes") or []

        for outcome in outcomes:
            name = outcome.get("name")
            price = to_float(outcome.get("price"))
            point = to_float(outcome.get("point"))

            if price is None:
                continue

            if key == "h2h":
                converted["outcomes"].append(
                    {
                        "name": name,
                        "price": price,
                    }
                )

            elif key == "spreads":
                converted["outcomes"].append(
                    {
                        "name": name,
                        "price": price,
                        "point": point,
                    }
                )

            elif key == "totals":
                converted["outcomes"].append(
                    {
                        "name": name,
                        "price": price,
                        "point": point,
                    }
                )

    if not converted["outcomes"]:
        return None

    return converted


def converted_markets_for_bookmaker(event, bookmaker):
    bookmaker_markets = get_bookmaker_markets(event, bookmaker)
    converted_markets = []

    for market in bookmaker_markets:
        converted_market = convert_market(event, market)
        if converted_market:
            converted_markets.append(converted_market)

    return converted_markets


def convert_event(event_by_bookmaker, event_fallback):
    selected_bookmaker = None
    selected_event = None
    converted_markets = []

    for bookmaker in BOOKMAKERS:
        candidate_event = event_by_bookmaker.get(bookmaker)

        if not candidate_event:
            continue

        candidate_markets = converted_markets_for_bookmaker(candidate_event, bookmaker)

        if candidate_markets:
            selected_bookmaker = bookmaker
            selected_event = candidate_event
            converted_markets = candidate_markets
            break

    if not selected_event or not converted_markets:
        return None, None

    last_update_values = [
        market.get("last_update")
        for market in converted_markets
        if market.get("last_update")
    ]

    bookmaker = {
        "key": "draftkings",
        "title": PRIMARY_BOOKMAKER,
        "last_update": max(last_update_values) if last_update_values else None,
        "markets": converted_markets,
    }

    return {
        "id": str(selected_event.get("id") or event_fallback.get("id")),
        "sport_key": "baseball_mlb",
        "sport_title": "MLB",
        "commence_time": selected_event.get("date") or event_fallback.get("date"),
        "home_team": selected_event.get("home") or event_fallback.get("home"),
        "away_team": selected_event.get("away") or event_fallback.get("away"),
        "bookmakers": [bookmaker],
    }, selected_bookmaker


events, event_counts = fetch_events()

if not events:
    print("No MLB events found with DraftKings or FanDuel odds.")
    data = []
    source_counts = {
        PRIMARY_BOOKMAKER: 0,
        FALLBACK_BOOKMAKER: 0,
    }
else:
    events_by_id = {
        str(event["id"]): event
        for event in events
        if event.get("id") is not None
    }

    event_ids = sorted(events_by_id.keys())
    raw_odds_by_id = fetch_odds(event_ids)

    data = []
    source_counts = {
        PRIMARY_BOOKMAKER: 0,
        FALLBACK_BOOKMAKER: 0,
    }

    for event_id in event_ids:
        converted, source_bookmaker = convert_event(
            raw_odds_by_id.get(event_id, {}),
            events_by_id[event_id],
        )

        if converted:
            data.append(converted)
            source_counts[source_bookmaker] = source_counts.get(source_bookmaker, 0) + 1

Path(path).parent.mkdir(parents=True, exist_ok=True)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Saved {path}")
print(f"{PRIMARY_BOOKMAKER} events found: {event_counts.get(PRIMARY_BOOKMAKER, 0)}")
print(f"{FALLBACK_BOOKMAKER} events found: {event_counts.get(FALLBACK_BOOKMAKER, 0)}")
print(f"Unique events found: {len(events)}")
print(f"Events with converted odds: {len(data)}")
print(f"Events using {PRIMARY_BOOKMAKER}: {source_counts.get(PRIMARY_BOOKMAKER, 0)}")
print(f"Events using {FALLBACK_BOOKMAKER}: {source_counts.get(FALLBACK_BOOKMAKER, 0)}")
