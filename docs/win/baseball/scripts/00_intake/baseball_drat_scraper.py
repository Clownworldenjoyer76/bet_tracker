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


def is_float(val: str) -> bool:
    try:
        float(val)
        return True
    except:
        return False


def detect_row_type(cells):
    """
    Determine if row is:
    - 'future' (has projections)
    - 'completed' (has final scores + log loss)
    - 'unknown'
    """

    # completed games → row[5] is scores like "6\n8"
    if len(cells) >= 7 and "\n" in cells[5]:
        parts = cells[5].split("\n")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return "completed"

    # future games → row[6] is projections like "3.4\n4.7" and row[7] is float
    if len(cells) >= 8 and "\n" in cells[6]:
        parts = cells[6].split("\n")
        if len(parts) == 2 and all(is_float(x) for x in parts) and is_float(cells[7]):
            return "future"

    return "unknown"


def normalize_row(cells):
    """
    Normalize all rows into a consistent structure.
    """

    row_type = detect_row_type(cells)

    try:
        # -------------------------
        # FUTURE GAME
        # -------------------------
        if row_type == "future":
            return {
                "type": "future",
                "raw": cells
            }

        # -------------------------
        # COMPLETED GAME
        # -------------------------
        elif row_type == "completed":
            return {
                "type": "completed",
                "raw": cells
            }

        # -------------------------
        # UNKNOWN
        # -------------------------
        else:
            log(f"UNKNOWN FORMAT ROW: {cells}")
            return None

    except Exception as e:
        log(f"NORMALIZE ERROR: {e} | ROW: {cells}")
        return None


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

            try:
                cells[0] = convert_utc_to_et(cells[0].replace("\n", " "))
            except:
                pass

            normalized = normalize_row(cells)

            if normalized:
                all_rows.append(normalized)
            else:
                log(f"SKIPPED ROW (failed normalization)")

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

            log(f"Normalized rows scraped: {len(raw)}")

            # breakdown for sanity
            future_count    = sum(1 for r in raw if r["type"] == "future")
            completed_count = sum(1 for r in raw if r["type"] == "completed")

            log(f"Future rows: {future_count}")
            log(f"Completed rows: {completed_count}")

            raw_path = raw_dir / f"{date}_mlb_raw.json"

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)

            files_written.append((str(raw_path), len(raw)))
            log(f"WROTE {raw_path} ({len(raw)} rows)")

            browser.close()

        log("--- SUMMARY ---")
        log(f"Rows scraped: {len(raw)}")
        log(f"Future rows: {future_count}")
        log(f"Completed rows: {completed_count}")
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
