#!/usr/bin/env python3
# docs/win/baseball/scripts/00_parsing/baseball_drat_scraper.py

import json
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd
from playwright.sync_api import sync_playwright

URLS = {
    "mlb": "https://www.dratings.com/predictor/mlb-baseball-predictions/",
}

UTC = pytz.utc
ET  = pytz.timezone("America/New_York")


def convert_utc_to_et(date_time_str: str) -> str:
    try:
        dt     = datetime.strptime(date_time_str.strip(), "%m/%d/%Y %I:%M %p")
        dt_utc = UTC.localize(dt)
        dt_et  = dt_utc.astimezone(ET)
        return dt_et.strftime("%m/%d/%Y %I:%M %p")
    except Exception:
        return date_time_str


def is_game_row(row):
    return len(row) >= 5 and "\n" in row[1]


def parse_mlb(row):
    if not is_game_row(row):
        return None

    try:
        # upcoming games format
        if len(row) >= 9 and row[-1] == "":
            date_time = convert_utc_to_et(row[0].replace("\n", " "))

            t = row[1].split("\n")
            team1, team2 = t[0].strip(), t[1].strip()

            wp = row[3].split("\n")
            wp1, wp2 = wp[0], wp[1]

            ml = row[4].split("\n")
            ml1, ml2 = ml[0], ml[1]

            sp = row[5].split("\n")
            sp1, sp2 = sp[0], sp[1]

            ps = row[6].split("\n")
            proj1, proj2 = ps[0], ps[1]

            total = row[7]

            ou = row[8].split("\n")
            over_line, under_line = ou[0], ou[1]

            return {
                "sport": "baseball",
                "league": "MLB",
                "date_time": date_time,
                "team1": team1,
                "team2": team2,
                "team1_win_pct": wp1,
                "team2_win_pct": wp2,
                "team1_moneyline": ml1,
                "team2_moneyline": ml2,
                "team1_spread": sp1,
                "team2_spread": sp2,
                "proj_score_1": proj1,
                "proj_score_2": proj2,
                "total": total,
                "over_line": over_line,
                "under_line": under_line,
                "score1": "",
                "score2": "",
                "game_status": "",
            }

        # completed games format
        elif len(row) == 7:
            date_time = convert_utc_to_et(row[0].replace("\n", " "))

            t = row[1].split("\n")
            team1, team2 = t[0].strip(), t[1].strip()

            wp = row[2].split("\n")
            wp1, wp2 = wp[0], wp[1]

            ml = row[3].split("\n")
            ml1, ml2 = ml[0], ml[1]

            sp = row[4].split("\n")
            sp1, sp2 = sp[0], sp[1]

            sc = row[5].split("\n")
            score1, score2 = sc[0], sc[1]

            return {
                "sport": "baseball",
                "league": "MLB",
                "date_time": date_time,
                "team1": team1,
                "team2": team2,
                "team1_win_pct": wp1,
                "team2_win_pct": wp2,
                "team1_moneyline": ml1,
                "team2_moneyline": ml2,
                "team1_spread": sp1,
                "team2_spread": sp2,
                "proj_score_1": "",
                "proj_score_2": "",
                "total": "",
                "over_line": "",
                "under_line": "",
                "score1": score1,
                "score2": score2,
                "game_status": "",
            }

    except:
        return None


def scrape_page(page, url):
    page.goto(url)
    page.wait_for_selector("table")
    rows = page.query_selector_all("table tbody tr")
    return [[c.inner_text().strip() for c in r.query_selector_all("td")] for r in rows]


def main():
    date = datetime.now(ET).strftime("%Y_%m_%d")

    raw_dir = Path("docs/win/baseball/00_intake/drat_raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    pred_dir = Path("docs/win/baseball/00_intake/predictions")
    pred_dir.mkdir(parents=True, exist_ok=True)

    scraper_dir = pred_dir / "scraper"
    scraper_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        })

        raw = scrape_page(page, URLS["mlb"])

        games = [parse_mlb(r) for r in raw]
        games = [g for g in games if g]

        raw_path = raw_dir / f"{date}_mlb_raw.json"
        with open(raw_path, "w") as f:
            json.dump(games, f, indent=2)

        upcoming = [g for g in games if g["score1"] == "" and g["proj_score_1"] != ""]

        if upcoming:
            df = pd.DataFrame(upcoming)

            scraper_path = scraper_dir / f"{date}_mlb_predictions.csv"
            df.to_csv(scraper_path, index=False)

        browser.close()


if __name__ == "__main__":
    main()
