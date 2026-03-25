import json
import time
import random
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

URLS = {
    "nba":        "https://www.dratings.com/predictor/nba-basketball-predictions/",
    "nhl":        "https://www.dratings.com/predictor/nhl-hockey-predictions/",
    "ncaa":       "https://www.dratings.com/predictor/ncaa-basketball-predictions/",
    "mlb":        "https://www.dratings.com/predictor/mlb-baseball-predictions/",
    "mls":        "https://www.dratings.com/predictor/mls-soccer-predictions/",
    "epl":        "https://www.dratings.com/predictor/english-premier-league-predictions/",
    "ligue1":     "https://www.dratings.com/predictor/france-ligue-1-predictions/",
    "laliga":     "https://www.dratings.com/predictor/spain-la-liga-predictions/",
    "bundesliga": "https://www.dratings.com/predictor/german-bundesliga-predictions/",
    "seriea":     "https://www.dratings.com/predictor/italy-serie-a-predictions/",
}

SPORT_PATHS = {
    "nba": "basketball",
    "ncaa": "basketball",
    "nhl": "hockey",
    "mlb": "baseball",
}

def is_game_row(row):
    return len(row) >= 5 and "\n" in row[1]

def parse_nba_ncaa(row, sport):
    if not is_game_row(row):
        return None
    try:
        date_time = row[0].replace("\n", " ")
        t = row[1].split("\n")
        team1, team2 = t[0].strip(), t[1].strip()

        w = row[2].split("\n")
        wp1, wp2 = w[0].strip(), w[1].strip()

        m = row[3].split("\n")
        ml1, ml2 = m[0].strip(), m[1].strip()

        s = row[4].split("\n")
        sp1, sp2 = s[0].strip(), s[1].strip()

        proj1 = proj2 = total = over_line = under_line = ""
        score1 = score2 = game_status = ""

        if len(row) >= 10 and "\n" in row[5]:
            ps = row[5].split("\n")
            proj1, proj2 = ps[0], ps[1]
            total = row[6]
            ou = row[7].split("\n")
            over_line, under_line = ou[0], ou[1]
        elif len(row) >= 9:
            total = row[5]
            ou = row[6].split("\n")
            over_line, under_line = ou[0], ou[1]
            game_status = " ".join(row[7].split("\n"))
            sc = row[8].split("\n")
            score1, score2 = sc[0], sc[1]

        return {
            "sport": sport,
            "date_time": date_time,
            "team1": team1,
            "team2": team2,
            "team1_moneyline": ml1,
            "team2_moneyline": ml2,
            "team1_spread": sp1,
            "team2_spread": sp2,
            "total": total,
            "over_line": over_line,
            "under_line": under_line,
        }
    except:
        return None

def parse_nhl_mlb(row, sport):
    if not is_game_row(row):
        return None
    try:
        date_time = row[0].replace("\n", " ")
        t = row[1].split("\n")
        team1, team2 = t[0].strip(), t[1].strip()

        m = row[4].split("\n")
        ml1, ml2 = m[0], m[1]

        s = row[5].split("\n")
        sp1, sp2 = s[0], s[1]

        total = row[7] if len(row) > 7 else ""

        return {
            "sport": sport,
            "date_time": date_time,
            "team1": team1,
            "team2": team2,
            "team1_moneyline": ml1,
            "team2_moneyline": ml2,
            "team1_spread": sp1,
            "team2_spread": sp2,
            "total": total,
        }
    except:
        return None

PARSERS = {
    "nba": parse_nba_ncaa,
    "ncaa": parse_nba_ncaa,
    "nhl": parse_nhl_mlb,
    "mlb": parse_nhl_mlb,
}

def scrape_page(page, url):
    page.goto(url)
    page.wait_for_selector("table")
    rows = page.query_selector_all("table tbody tr")
    return [[c.inner_text().strip() for c in r.query_selector_all("td")] for r in rows]

def main():
    date = datetime.utcnow().strftime("%Y_%m_%d")

    all_games = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for sport, url in URLS.items():
            print(f"Scraping {sport}")
            raw = scrape_page(page, url)

            parser = PARSERS.get(sport)
            if not parser:
                continue

            games = [parser(r, sport) for r in raw]
            games = [g for g in games if g]

            all_games[sport] = games

            time.sleep(random.uniform(2, 4))

        browser.close()

    for sport, games in all_games.items():
        if sport not in SPORT_PATHS or not games:
            continue

        folder = SPORT_PATHS[sport]

        path = f"docs/win/{folder}/00_intake/predictions/scraper/{date}_{sport}.csv"
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        pd.DataFrame(games).to_csv(path, index=False)

        print(f"Saved {path}")

if __name__ == "__main__":
    main()
