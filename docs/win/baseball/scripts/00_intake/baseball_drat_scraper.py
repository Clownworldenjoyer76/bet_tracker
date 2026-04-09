#!/usr/bin/env python3
# docs/win/baseball/scripts/00_intake/baseball_drat_scraper.py

import json
import traceback
from pathlib import Path
from datetime import datetime
import pytz
from playwright.sync_api import sync_playwright

URLS = {
    "mlb": "https://www.dratings.com/predictor/mlb-baseball-predictions/",
}

UTC = pytz.utc
ET  = pytz.timezone("America/New_York")

ERROR_DIR = Path("docs/win/baseball/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "baseball_drat_scraper.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== baseball_drat_scraper RUN {datetime.now(ET).isoformat()} ===\n")


def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(ET).isoformat()} | {msg}\n")


def convert_utc_to_et(date_time_str: str) -> str:
    try:
        dt     = datetime.strptime(date_time_str.strip(), "%m/%d/%Y %I:%M %p")
        dt_utc = UTC.localize(dt)
        dt_et  = dt_utc.astimezone(ET)
        return dt_et.strftime("%m/%d/%Y %I:%M %p")
    except Exception:
        return date_time_str


def is_completed_row(cells):
    """
    Correct detection:
    - row[5] must be scores like "6\n8"
    - BOTH values must be integers
    """

    try:
        if len(cells) >= 6 and "\n" in cells[5]:
            parts = [x.strip() for x in cells[5].split("\n")]

            if len(parts) == 2 and all(p.isdigit() for p in parts):
                return True

    except:
        pass

    return False


def scrape_page(page, url):
    page.goto(url)
    page.wait_for_selector("table")

    all_rows = []
    tables   = page.query_selector_all("table")

    for table in tables:
        rows = table.query_selector_all("tbody tr")

        for r in rows:
            cells = [c.inner_text().strip() for c in r.query_selector_all("td")]

            if not cells:
                continue

            # normalize datetime
            try:
                cells[0] = convert_utc_to_et(cells[0].replace("\n", " "))
            except:
                pass

            # -------------------------
            # FIXED DETECTION
            # -------------------------
            if is_completed_row(cells):
                log(f"COMPLETED ROW DETECTED: {cells[1]}")

                # truncate to ensure transform handles correctly
                cells = cells[:6]

            all_rows.append(cells)

    return all_rows


def main():
    files_written = []

    try:
        date = datetime.now(ET).strftime("%Y_%m_%d")

        raw_dir = Path("docs/win/baseball/00_intake/drat_raw")
        raw_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()

            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            })

            raw = scrape_page(page, URLS["mlb"])
            log(f"Raw rows scraped: {len(raw)}")

            raw_path = raw_dir / f"{date}_mlb_raw.json"

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)

            files_written.append((str(raw_path), len(raw)))
            log(f"WROTE {raw_path} ({len(raw)} rows)")

            browser.close()

        log("--- SUMMARY ---")
        log(f"Raw rows scraped: {len(raw)}")
        log(f"Files written: {len(files_written)}")

        for path, count in files_written:
            log(f"  FILE: {path} ({count} rows)")

        log("STATUS: SUCCESS")

    except Exception as e:
        log(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
        log("STATUS: FAILED")
        raise

    print("Baseball drat scraper complete.")


if __name__ == "__main__":
    main()
