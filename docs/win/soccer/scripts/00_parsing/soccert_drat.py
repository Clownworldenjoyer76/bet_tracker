import time
import random
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

URLS = {
    "mls":        "https://www.dratings.com/predictor/mls-soccer-predictions/",
    "epl":        "https://www.dratings.com/predictor/english-premier-league-predictions/",
    "ligue1":     "https://www.dratings.com/predictor/france-ligue-1-predictions/",
    "laliga":     "https://www.dratings.com/predictor/spain-la-liga-predictions/",
    "bundesliga": "https://www.dratings.com/predictor/german-bundesliga-predictions/",
    "seriea":     "https://www.dratings.com/predictor/italy-serie-a-predictions/",
}

LEAGUE_MAP = {
    "mls": "MLS",
    "epl": "EPL",
    "ligue1": "LIGUE1",
    "laliga": "LALIGA",
    "bundesliga": "BUNDESLIGA",
    "seriea": "SERIEA",
}

def scrape_page(page, url):
    page.goto(url)
    page.wait_for_selector("table")
    rows = page.query_selector_all("table tbody tr")
    return [[c.inner_text().strip() for c in r.query_selector_all("td")] for r in rows]

def split_date_time(dt):
    date, time_ = dt.split("|")
    date = datetime.strptime(date.strip(), "%m/%d/%Y").strftime("%Y_%m_%d")
    return date, time_.strip()

def parse_prediction(row, league):
    try:
        date, time_ = split_date_time(row[0])

        teams = row[1].split("\n")
        home, away = teams[0].strip(), teams[1].strip()

        probs = row[2].split("\n")
        home_prob = probs[0].strip()
        away_prob = probs[1].strip()

        draw_prob = row[3].strip()

        xg = row[5].split("\n") if len(row) > 5 and row[5] else ["", ""]
        home_xg = xg[0]
        away_xg = xg[1] if len(xg) > 1 else ""

        total = row[6] if len(row) > 6 else ""

        return {
            "sport": "soccer",
            "league": league,
            "market": "",
            "match_date": date,
            "match_time": time_,
            "home_team": home,
            "away_team": away,
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "expected_total_goals": total,
        }
    except Exception as e:
        print(f"[DEBUG][PREDICTION PARSE ERROR] {league} | row={row} | error={e}")
        return None

def parse_final(row, league):
    try:
        date, time_ = split_date_time(row[0])

        teams = row[1].split("\n")
        home, away = teams[0].strip(), teams[1].strip()

        score = row[5].split("\n")
        home_score = score[0]
        away_score = score[1]

        return {
            "sport": "soccer",
            "league": league,
            "market": "",
            "game_date": date,
            "match_time": time_,
            "home_team": home,
            "away_team": away,
            "away_score": away_score,
            "home_score": home_score,
        }
    except Exception as e:
        print(f"[DEBUG][FINAL PARSE ERROR] {league} | row={row} | error={e}")
        return None

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for key, url in URLS.items():
            league = LEAGUE_MAP[key]
            print(f"\n--- Scraping {league} ---")

            raw = scrape_page(page, url)
            print(f"[DEBUG] Total rows scraped: {len(raw)}")

            predictions = []
            finals = []

            for i, r in enumerate(raw):
                print(f"\n[DEBUG] Row {i}: {r}")

                # skip junk rows
                if not r or "Sportsbooks" in r[0] or "DRatings" in r[0]:
                    print(f"[DEBUG] Skipped junk row {i}")
                    continue

                # classification debug
                col4 = r[4] if len(r) > 4 else None
                print(f"[DEBUG] Row {i} col4 value: '{col4}'")

                if col4 == "":
                    print(f"[DEBUG] Row {i} classified as PREDICTION")
                    parsed = parse_prediction(r, league)
                    if parsed:
                        predictions.append(parsed)
                else:
                    print(f"[DEBUG] Row {i} classified as FINAL")
                    parsed = parse_final(r, league)
                    if parsed:
                        finals.append(parsed)

            print(f"\n[DEBUG] {league} → predictions: {len(predictions)}, finals: {len(finals)}")

            today = datetime.utcnow().strftime("%Y_%m_%d")

            pred_path = Path(f"docs/win/soccer/00_intake/predictions/{league}/{today}_{league}.csv")
            pred_path.parent.mkdir(parents=True, exist_ok=True)

            final_path = Path(f"docs/win/final_scores/results/soccer/final_scores/{league}/{today}_{league}.csv")
            final_path.parent.mkdir(parents=True, exist_ok=True)

            if predictions:
                pd.DataFrame(predictions).to_csv(pred_path, index=False)
                print(f"[DEBUG] Saved predictions → {pred_path}")
            else:
                print(f"[DEBUG] No predictions saved for {league}")

            if finals:
                pd.DataFrame(finals).to_csv(final_path, index=False)
                print(f"[DEBUG] Saved finals → {final_path}")
            else:
                print(f"[DEBUG] No finals saved for {league}")

            time.sleep(random.uniform(2, 4))

        browser.close()

if __name__ == "__main__":
    main()
