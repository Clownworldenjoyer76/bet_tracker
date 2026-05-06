# docs/win/soccer/scripts/00_intake/soccer_drat.py

import json
import re
import time
import random
import traceback
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

ERROR_DIR = Path("docs/win/soccer/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "soccer_drat.txt"

RAW_DIR = Path("docs/win/soccer/00_intake/predictions/drat_raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== soccer_drat RUN {datetime.now(timezone.utc).isoformat()} ===\n")


def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")


files_written = []

URLS = {
    "mls":        "https://www.dratings.com/predictor/mls-soccer-predictions/",
    "epl":        "https://www.dratings.com/predictor/english-premier-league-predictions/",
    "ligue1":     "https://www.dratings.com/predictor/france-ligue-1-predictions/",
    "laliga":     "https://www.dratings.com/predictor/spain-la-liga-predictions/",
    "bundesliga": "https://www.dratings.com/predictor/german-bundesliga-predictions/",
    "seriea":     "https://www.dratings.com/predictor/italy-serie-a-predictions/",
}

LEAGUE_MAP = {
    "mls":        "MLS",
    "epl":        "EPL",
    "ligue1":     "LIGUE1",
    "laliga":     "LALIGA",
    "bundesliga": "BUNDESLIGA",
    "seriea":     "SERIEA",
}

# Only MLS needs this based on sportsbook comparison:
# DRatings MLS 2026_05_10 12:30 AM == sportsbook 2026_05_09 08:30 PM
MLS_TIME_SHIFT_HOURS = -4

MLS_RECORD_PAT = re.compile(r"\s*\(\d+-\d+-\d+\)\s*$")


def strip_record(name: str) -> str:
    return MLS_RECORD_PAT.sub("", name).strip()


def scrape_page(page, url):
    page.goto(url)
    page.wait_for_selector("table")
    rows = page.query_selector_all("table tbody tr")

    result = []
    for i, r in enumerate(rows):
        cells = [c.inner_text().strip() for c in r.query_selector_all("td")]
        result.append({
            "row_number": i + 1,
            "cell_count": len(cells),
            "cells": cells,
        })

    return result


def dump_raw(league: str, today: str, raw_rows: list) -> None:
    raw_path = RAW_DIR / f"{league}_{today}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_rows, f, indent=2, ensure_ascii=False)

    log(f"RAW DUMP → {raw_path} ({len(raw_rows)} rows)")


def split_date_time(dt: str, shift_hours: int = 0):
    parts = dt.replace("\n", " ").split()

    raw_date = parts[0]
    raw_time = " ".join(parts[1:])

    parsed = datetime.strptime(f"{raw_date} {raw_time}", "%m/%d/%Y %I:%M %p")

    if shift_hours:
        parsed = parsed + timedelta(hours=shift_hours)

    date = parsed.strftime("%Y_%m_%d")
    time_ = parsed.strftime("%I:%M %p")

    return date, time_


def league_time_shift(league: str) -> int:
    return MLS_TIME_SHIFT_HOURS if league == "MLS" else 0


def safe_split(val: str) -> list:
    return val.split("\n") if "\n" in val else val.split()


def is_prediction(cells: list) -> bool:
    return len(cells) == 10


def is_final(cells: list) -> bool:
    return len(cells) == 8


def parse_prediction(cells: list, league: str) -> dict | None:
    try:
        date, time_ = split_date_time(cells[0], league_time_shift(league))

        teams = safe_split(cells[1])
        away_team = strip_record(teams[0])
        home_team = strip_record(teams[1]) if len(teams) > 1 else ""

        probs = safe_split(cells[2])
        away_prob = probs[0] if len(probs) > 0 else ""
        home_prob = probs[1] if len(probs) > 1 else ""

        draw_prob = cells[3]

        xg = safe_split(cells[5])
        away_xg = xg[0] if len(xg) > 0 else ""
        home_xg = xg[1] if len(xg) > 1 else ""

        total = cells[6]

        return {
            "sport": "soccer",
            "league": league,
            "market": "",
            "match_date": date,
            "match_time": time_,
            "home_team": home_team,
            "away_team": away_team,
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "expected_total_goals": total,
        }

    except Exception as e:
        log(f"PREDICTION PARSE ERROR {league} | {cells} | {e}")
        return None


def parse_final(cells: list, league: str) -> dict | None:
    try:
        date, time_ = split_date_time(cells[0], league_time_shift(league))

        teams = safe_split(cells[1])
        away_team = strip_record(teams[0])
        home_team = strip_record(teams[1]) if len(teams) > 1 else ""

        score = safe_split(cells[5])
        away_score = score[0] if len(score) > 0 else ""
        home_score = score[1] if len(score) > 1 else ""

        return {
            "sport": "soccer",
            "league": league,
            "market": "",
            "game_date": date,
            "match_time": time_,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
        }

    except Exception as e:
        log(f"FINAL PARSE ERROR {league} | {cells} | {e}")
        return None


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        today = datetime.now(timezone.utc).strftime("%Y_%m_%d")

        for key, url in URLS.items():
            league = LEAGUE_MAP[key]
            log(f"Scraping {league}")

            try:
                raw_rows = scrape_page(page, url)
                dump_raw(league, today, raw_rows)

                predictions = []
                finals = []

                for row in raw_rows:
                    cells = row["cells"]

                    if not cells or any(kw in cells[0] for kw in ("Sportsbooks", "DRatings")):
                        continue

                    if is_prediction(cells):
                        parsed = parse_prediction(cells, league)
                        if parsed:
                            predictions.append(parsed)

                    elif is_final(cells):
                        parsed = parse_final(cells, league)
                        if parsed:
                            finals.append(parsed)

                    else:
                        log(f"SKIPPED unknown row ({len(cells)} cells) | {cells}")

                log(f"{league} → predictions: {len(predictions)}, finals: {len(finals)}")
                print(f"\n--- {league} → predictions: {len(predictions)}, finals: {len(finals)} ---")

                if predictions:
                    pred_df = pd.DataFrame(predictions)
                    pred_df = pred_df[[
                        "sport", "league", "market", "match_date", "match_time",
                        "home_team", "away_team", "home_prob", "draw_prob", "away_prob",
                        "home_xg", "away_xg", "expected_total_goals",
                    ]]

                    for match_date, group in pred_df.groupby("match_date"):
                        pred_path = Path(
                            f"docs/win/soccer/00_intake/predictions/{league}/{match_date}_{league}.csv"
                        )
                        pred_path.parent.mkdir(parents=True, exist_ok=True)
                        group.to_csv(pred_path, index=False)

                        files_written.append((str(pred_path), group.iloc[0].to_dict()))
                        log(f"WROTE predictions → {pred_path} ({len(group)} rows)")

                if finals:
                    final_df = pd.DataFrame(finals)
                    final_df = final_df[[
                        "sport", "league", "market", "game_date", "match_time",
                        "home_team", "away_team", "home_score", "away_score",
                    ]]

                    for game_date, group in final_df.groupby("game_date"):
                        final_path = Path(
                            f"docs/win/final_scores/results/soccer/final_scores/{league}/{game_date}_{league}.csv"
                        )
                        final_path.parent.mkdir(parents=True, exist_ok=True)
                        group.to_csv(final_path, index=False)

                        files_written.append((str(final_path), group.iloc[0].to_dict()))
                        log(f"WROTE finals → {final_path} ({len(group)} rows)")

            except Exception as e:
                log(f"ERROR scraping {league}: {e}\n{traceback.format_exc()}")

            time.sleep(random.uniform(2, 4))

        browser.close()

    log("--- FILES WRITTEN ---")

    if files_written:
        for path, sample in files_written:
            log(f"  FILE: {path}")
            log(f"  SAMPLE ROW: {sample}")
    else:
        log("  No files written.")

    log("STATUS: SUCCESS")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
        log("STATUS: FAILED")
        raise
