import os
import csv
import requests
from collections import defaultdict
from datetime import datetime, timezone

API_KEY = os.environ["CLOUD_API"]

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

BASE_PATH = "docs/win/soccer/00_intake/sportsbook"
os.makedirs(BASE_PATH, exist_ok=True)

LEAGUES = {
    "soccer-england-premier-league": "EPL",
    "soccer-spain-laliga": "La Liga",
    "soccer-france-ligue-1": "Ligue 1",
    "soccer-germany-bundesliga": "Bundesliga",
    "soccer-italy-serie-a": "Serie A",
    "soccer-usa-major-league-soccer": "MLS",
}

FIELDNAMES = [
    "sport",
    "league",
    "game_id",
    "match_date",
    "match_time",
    "home_team",
    "away_team",
    "dk_home_decimal",
    "dk_draw_decimal",
    "dk_away_decimal",
    "dk_over25_decimal",
    "dk_under25_decimal",
    "dk_over35_decimal",
    "dk_under35_decimal",
    "btts_yes",
    "btts_no",
]


def get_json(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_start_time(game: dict) -> tuple[str, str] | tuple[None, None]:
    raw = game.get("startTime") or game.get("cutoffTime")
    if not raw:
        return None, None

    dt = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    match_date = dt.strftime("%Y-%m-%d")
    match_time = dt.strftime("%I:%M %p")
    return match_date, match_time


def interpolate(lines: dict[float, float], target: float) -> float | None:
    if target in lines:
        return lines[target]

    lower = max((k for k in lines if k < target), default=None)
    upper = min((k for k in lines if k > target), default=None)

    if lower is not None and upper is not None:
        return round((lines[lower] + lines[upper]) / 2, 3)

    return None


def extract_match_odds(markets: dict) -> tuple[float | None, float | None, float | None]:
    home = draw = away = None
    market = markets.get("soccer.match_odds")
    if not market:
        return home, draw, away

    for sub in market.get("submarkets", {}).values():
        for sel in sub.get("selections", []):
            outcome = sel.get("outcome")
            price = sel.get("price")
            if outcome == "home":
                home = price
            elif outcome == "draw":
                draw = price
            elif outcome == "away":
                away = price

    return home, draw, away


def extract_btts(markets: dict) -> tuple[float | None, float | None]:
    yes = no = None
    market = markets.get("soccer.both_teams_to_score")
    if not market:
        return yes, no

    for sub in market.get("submarkets", {}).values():
        for sel in sub.get("selections", []):
            outcome = sel.get("outcome")
            price = sel.get("price")
            if outcome == "yes":
                yes = price
            elif outcome == "no":
                no = price

    return yes, no


def extract_totals(markets: dict) -> tuple[float | None, float | None, float | None, float | None]:
    over_lines: dict[float, float] = {}
    under_lines: dict[float, float] = {}

    market = markets.get("soccer.total_goals")
    if not market:
        return None, None, None, None

    for sub in market.get("submarkets", {}).values():
        for sel in sub.get("selections", []):
            params = str(sel.get("params", ""))
            price = sel.get("price")
            outcome = sel.get("outcome")

            if "total=" not in params or price is None:
                continue

            try:
                line = float(params.split("total=")[1].split("&")[0])
            except ValueError:
                continue

            if outcome == "over":
                over_lines[line] = price
            elif outcome == "under":
                under_lines[line] = price

    over25 = interpolate(over_lines, 2.5)
    under25 = interpolate(under_lines, 2.5)
    over35 = interpolate(over_lines, 3.5)
    under35 = interpolate(under_lines, 3.5)

    return over25, under25, over35, under35


def main() -> None:
    rows_by_date: dict[str, list[dict]] = defaultdict(list)

    for league_key, league_name in LEAGUES.items():
        competition_url = f"https://sports-api.cloudbet.com/pub/v2/odds/competitions/{league_key}"
        competition = get_json(competition_url)

        for event in competition.get("events", []):
            home = event.get("home") or {}
            away = event.get("away") or {}

            if not home.get("name") or not away.get("name"):
                continue

            event_id = event.get("id")
            if not event_id:
                continue

            event_url = f"https://sports-api.cloudbet.com/pub/v2/odds/events/{event_id}"
            game = get_json(event_url)
            markets = game.get("markets") or {}

            match_date, match_time = parse_start_time(game)
            if not match_date or not match_time:
                continue

            dk_home_decimal, dk_draw_decimal, dk_away_decimal = extract_match_odds(markets)
            dk_over25_decimal, dk_under25_decimal, dk_over35_decimal, dk_under35_decimal = extract_totals(markets)
            btts_yes, btts_no = extract_btts(markets)

            row = {
                "sport": "soccer",
                "league": league_name,
                "game_id": game.get("id"),
                "match_date": match_date,
                "match_time": match_time,
                "home_team": (game.get("home") or {}).get("name"),
                "away_team": (game.get("away") or {}).get("name"),
                "dk_home_decimal": dk_home_decimal,
                "dk_draw_decimal": dk_draw_decimal,
                "dk_away_decimal": dk_away_decimal,
                "dk_over25_decimal": dk_over25_decimal,
                "dk_under25_decimal": dk_under25_decimal,
                "dk_over35_decimal": dk_over35_decimal,
                "dk_under35_decimal": dk_under35_decimal,
                "btts_yes": btts_yes,
                "btts_no": btts_no,
            }

            if any(
                row[k] is not None
                for k in (
                    "dk_home_decimal",
                    "dk_draw_decimal",
                    "dk_away_decimal",
                    "dk_over25_decimal",
                    "dk_under25_decimal",
                    "dk_over35_decimal",
                    "dk_under35_decimal",
                    "btts_yes",
                    "btts_no",
                )
            ):
                rows_by_date[match_date].append(row)

    for match_date, rows in rows_by_date.items():
        rows.sort(key=lambda r: (r["match_time"], r["league"], r["home_team"], r["away_team"]))
        out_path = os.path.join(BASE_PATH, f"{match_date}_soccer.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    total_rows = sum(len(v) for v in rows_by_date.values())
    print(f"Wrote {total_rows} rows across {len(rows_by_date)} files.")


if __name__ == "__main__":
    main()
