"""
dratings.com Multi-Sport Predictions Scraper
Uses Playwright + per-sport parsers to handle different table layouts.

Install dependencies:
    pip install playwright pandas
    python -m playwright install chromium
"""

import json
import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright


# Add or remove URLs here
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
    # "nfl":      "https://www.dratings.com/predictor/nfl-football-predictions/",
}

# Sports that include a goalie/pitcher/starter column
SPORTS_WITH_STARTER = {"nhl", "mlb"}

# Sports that use 3-way win% (home/draw/away) instead of 2-way
SPORTS_WITH_DRAW = {"mls"}


def is_game_row(row: list) -> bool:
    """True if this looks like a matchup row (has teams with a newline separator)."""
    return len(row) >= 5 and "\n" in row[1]


def parse_nba_ncaa(row: list, sport: str) -> dict | None:
    """
    NBA / NCAAB layout (no starter column):
    [0] date_time
    [1] team1\nteam2
    [2] win_pct1\nwin_pct2
    [3] ml1\nml2
    [4] spread1\nspread2
    Upcoming (10 cols):
      [5] proj1\nproj2  [6] total  [7] over_under  [8] ""  [9] ""
    Live (9 cols):
      [5] total  [6] over_under  [7] period\ntime  [8] score1\nscore2
    Final (8 cols):
      [5] score1\nscore2  [6] stat  [7] stat
    """
    if not is_game_row(row):
        return None
    try:
        date_time = row[0].replace("\n", " ")
        t = row[1].split("\n")
        team1, team2 = t[0].strip(), t[1].strip() if len(t) > 1 else ""

        w = row[2].split("\n")
        wp1, wp2 = w[0].strip(), w[1].strip() if len(w) > 1 else ""

        m = row[3].split("\n")
        ml1, ml2 = m[0].strip(), m[1].strip() if len(m) > 1 else ""

        s = row[4].split("\n")
        sp1, sp2 = s[0].strip(), s[1].strip() if len(s) > 1 else ""

        # Determine layout by checking if col[5] has a newline (upcoming) or not
        proj1 = proj2 = total = over_line = under_line = game_status = score1 = score2 = ""

        over_line = under_line = ""

        if len(row) >= 10 and "\n" in row[5]:
            # Upcoming
            ps = row[5].split("\n")
            proj1, proj2 = ps[0].strip(), ps[1].strip() if len(ps) > 1 else ""
            total = row[6].strip()
            ou = row[7].split("\n")
            over_line  = ou[0].strip() if len(ou) > 0 else ""
            under_line = ou[1].strip() if len(ou) > 1 else ""
        elif len(row) >= 9 and "\n" not in row[5]:
            # Live game
            total = row[5].strip()
            ou = row[6].split("\n")
            over_line  = ou[0].strip() if len(ou) > 0 else ""
            under_line = ou[1].strip() if len(ou) > 1 else ""
            gs = row[7].split("\n")
            game_status = " ".join(gs).strip()
            sc = row[8].split("\n")
            score1 = sc[0].strip()
            score2 = sc[1].strip() if len(sc) > 1 else ""
        elif len(row) >= 7:
            # Final
            sc = row[5].split("\n")
            score1 = sc[0].strip()
            score2 = sc[1].strip() if len(sc) > 1 else ""

        return {
            "sport": sport.upper(), "date_time": date_time,
            "team1": team1, "team2": team2,
            "team1_win_pct": wp1, "team2_win_pct": wp2,
            "team1_moneyline": ml1, "team2_moneyline": ml2,
            "team1_spread": sp1, "team2_spread": sp2,
            "proj_score_1": proj1, "proj_score_2": proj2,
            "total": total, "over_line": over_line, "under_line": under_line,
            "score1": score1, "score2": score2,
            "game_status": game_status,
        }
    except Exception as e:
        print(f"  parse error (nba/ncaa): {e} | {row}")
        return None


def parse_nhl_mlb(row: list, sport: str) -> dict | None:
    """
    NHL / MLB layout (has starter/goalie column at index 2):
    [0] date_time
    [1] team1\nteam2
    [2] starter1\nstarter2   <-- extra column vs NBA
    [3] win_pct1\nwin_pct2
    [4] ml1\nml2
    [5] spread1\nspread2
    Upcoming (11 cols):
      [6] proj1\nproj2  [7] total  [8] over_under  [9] ""  [10] ""
    Live (9-10 cols):
      [6] total  [7] over_under  [8] period\ntime  [9] score1\nscore2
    Final (8 cols):
      [6] score1\nscore2  [7] stat  ...
    """
    if not is_game_row(row):
        return None

    # Detect if starter column is present: col[2] won't have % signs
    has_starter = len(row) > 2 and "%" not in row[2] and "\n" in row[2]
    offset = 1 if has_starter else 0

    try:
        date_time = row[0].replace("\n", " ")
        t = row[1].split("\n")
        team1, team2 = t[0].strip(), t[1].strip() if len(t) > 1 else ""

        starter1 = starter2 = ""
        if has_starter:
            st = row[2].split("\n")
            starter1 = st[0].strip()
            starter2 = st[1].strip() if len(st) > 1 else ""

        w = row[2 + offset].split("\n")
        wp1, wp2 = w[0].strip(), w[1].strip() if len(w) > 1 else ""

        m = row[3 + offset].split("\n")
        ml1, ml2 = m[0].strip(), m[1].strip() if len(m) > 1 else ""

        s = row[4 + offset].split("\n")
        sp1, sp2 = s[0].strip(), s[1].strip() if len(s) > 1 else ""

        proj1 = proj2 = total = over_line = under_line = game_status = score1 = score2 = ""
        base = 5 + offset

        def looks_like_total(s: str) -> bool:
            """Real totals are positive numbers like 5.56 or 231.2"""
            try:
                return float(s) > 0
            except ValueError:
                return False

        def looks_like_game_status(s: str) -> bool:
            """Live/final status contains period/quarter/half info"""
            keywords = ["P", "Q", "H", "END", "HALF", "OT", "Final"]
            return any(k in s for k in keywords)

        def looks_like_score(s: str) -> bool:
            """Small non-negative integer = a score, not a projected score."""
            try:
                v = float(s)
                return v >= 0 and v == int(v) and v < 30
            except ValueError:
                return False

        if len(row) > base and "\n" in row[base] and not looks_like_score(row[base].split("\n")[0]):
            # Upcoming: proj scores in same cell (decimals like 2.88)
            ps = row[base].split("\n")
            proj1, proj2 = ps[0].strip(), ps[1].strip() if len(ps) > 1 else ""
            total = row[base + 1].strip() if len(row) > base + 1 else ""
            ou = row[base + 2].split("\n") if len(row) > base + 2 else []
            over_line  = ou[0].strip() if len(ou) > 0 else ""
            under_line = ou[1].strip() if len(ou) > 1 else ""
        elif len(row) > base + 3 and looks_like_total(row[base]) and looks_like_game_status(row[base + 2]):
            # Live: total, over/under, status, scores
            total = row[base].strip()
            ou = row[base + 1].split("\n")
            over_line  = ou[0].strip() if len(ou) > 0 else ""
            under_line = ou[1].strip() if len(ou) > 1 else ""
            gs = row[base + 2].split("\n")
            game_status = " ".join(gs).strip()
            sc = row[base + 3].split("\n")
            score1 = sc[0].strip()
            score2 = sc[1].strip() if len(sc) > 1 else ""
        elif len(row) > base:
            # Final: scores either in one "s1\ns2" cell or two separate cells
            sc = row[base].split("\n")
            score1 = sc[0].strip()
            if len(sc) > 1:
                score2 = sc[1].strip()
            elif len(row) > base + 1:
                candidate = row[base + 1].strip()
                try:
                    val = float(candidate)
                    score2 = candidate if val >= 0 else ""
                except ValueError:
                    score2 = ""


        return {
            "sport": sport.upper(), "date_time": date_time,
            "team1": team1, "team2": team2,
            "starter1": starter1, "starter2": starter2,
            "team1_win_pct": wp1, "team2_win_pct": wp2,
            "team1_moneyline": ml1, "team2_moneyline": ml2,
            "team1_spread": sp1, "team2_spread": sp2,
            "proj_score_1": proj1, "proj_score_2": proj2,
            "total": total, "over_line": over_line, "under_line": under_line,
            "score1": score1, "score2": score2,
            "game_status": game_status,
        }
    except Exception as e:
        print(f"  parse error (nhl/mlb): {e} | {row}")
        return None


def parse_mls(row: list, sport: str) -> dict | None:
    """
    Soccer layout (MLS, EPL, Ligue1, LaLiga, Bundesliga, Serie A):
    [0] date_time
    [1] team1\nteam2

    Completed / live games (moneyline format, e.g. +300):
      [2] home_win%\naway_win%  [3] draw_pct  [4] ml1\nml2  [5] score1\nscore2

    Upcoming games with decimal odds (e.g. 1.89 / 2.56):
      [2] home_win%\naway_win%  [3] draw_pct  [4] proj_home\nproj_away
      OR
      [2] home_win%\naway_win%  [3] draw_pct  [4] ml1  [5] ml2  (rare)

    Some upcoming games have no win% at all — cols shift left.
    """
    if not is_game_row(row):
        return None
    try:
        date_time = row[0].replace("\n", " ")
        t = row[1].split("\n")
        team1, team2 = t[0].strip(), t[1].strip() if len(t) > 1 else ""

        home_win_pct = draw_pct = away_win_pct = ""
        ml1 = ml2 = score1 = score2 = proj1 = proj2 = ""

        def looks_like_decimal_odd(s: str) -> bool:
            """True if string looks like a decimal odd (e.g. '1.89', '2.56')."""
            try:
                v = float(s)
                return 1.0 <= v <= 20.0
            except ValueError:
                return False

        def looks_like_american_odd(s: str) -> bool:
            """True if string looks like an American moneyline (e.g. '+300', '-150')."""
            return s.startswith("+") or s.startswith("-")

        # col[2]: could be "home%\naway%" or a single win% or a decimal odd
        col2 = row[2] if len(row) > 2 else ""
        col2_parts = col2.split("\n")

        if len(col2_parts) >= 2 and "%" in col2_parts[0]:
            # Standard: home%\naway% in col2, draw in col3
            home_win_pct = col2_parts[0].strip()
            away_win_pct = col2_parts[1].strip()
            draw_pct = row[3].strip() if len(row) > 3 else ""
            odds_col = 4
        elif "%" in col2:
            # Single win% in col2
            home_win_pct = col2.strip()
            draw_pct = row[3].strip() if len(row) > 3 else ""
            away_win_pct = row[4].strip() if len(row) > 4 else ""
            odds_col = 5
        else:
            # No win% found — odds start at col2
            odds_col = 2

        if len(row) > odds_col:
            odds_val = row[odds_col]
            odds_parts = odds_val.split("\n")

            if looks_like_decimal_odd(odds_parts[0]):
                # Upcoming game with decimal projected scores
                proj1 = odds_parts[0].strip()
                proj2 = odds_parts[1].strip() if len(odds_parts) > 1 else ""
            elif looks_like_american_odd(odds_parts[0]):
                # Completed/live game with American moneylines
                ml1 = odds_parts[0].strip()
                ml2 = odds_parts[1].strip() if len(odds_parts) > 1 else ""
                # Score is in next column
                if len(row) > odds_col + 1:
                    sc = row[odds_col + 1].split("\n")
                    score1 = sc[0].strip()
                    score2 = sc[1].strip() if len(sc) > 1 else ""

        return {
            "sport":           sport.upper(),
            "date_time":       date_time,
            "team1":           team1,
            "team2":           team2,
            "home_win_pct":    home_win_pct,
            "draw_pct":        draw_pct,
            "away_win_pct":    away_win_pct,
            "team1_moneyline": ml1,
            "team2_moneyline": ml2,
            "proj_score_1":    proj1,
            "proj_score_2":    proj2,
            "score1":          score1,
            "score2":          score2,
        }
    except Exception as e:
        print(f"  parse error (soccer): {e} | {row}")
        return None


PARSERS = {
    "nba":        parse_nba_ncaa,
    "ncaa":       parse_nba_ncaa,
    "nhl":        parse_nhl_mlb,
    "mlb":        parse_nhl_mlb,
    "mls":        parse_mls,
    "epl":        parse_mls,
    "ligue1":     parse_mls,
    "laliga":     parse_mls,
    "bundesliga": parse_mls,
    "seriea":     parse_mls,
}


def scrape_page(page, url: str) -> list[list]:
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_selector("table", timeout=15000)
    rows = page.query_selector_all("table tbody tr")
    return [[c.inner_text().strip() for c in r.query_selector_all("td")] for r in rows]


def main():
    all_games: dict[str, list[dict]] = {}
    all_raw: dict[str, list] = {}

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

        for sport, url in URLS.items():
            print(f"\nScraping {sport.upper()}: {url}")
            try:
                raw = scrape_page(page, url)
                all_raw[sport] = raw
                parser = PARSERS.get(sport, parse_nba_ncaa)
                games = [parser(r, sport) for r in raw]
                games = [g for g in games if g is not None]
                all_games[sport] = games
                print(f"  -> {len(games)} games found")
            except Exception as e:
                print(f"  ERROR: {e}")

            delay = random.uniform(2, 5)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)

        browser.close()

    if not any(all_games.values()):
        print("\nNo data found.")
        return

    # Save one CSV per sport + one combined
    for sport, games in all_games.items():
        if games:
            pd.DataFrame(games).to_csv(f"{sport}_predictions.csv", index=False)
            print(f"Saved {sport}_predictions.csv ({len(games)} rows)")

    all_flat = [g for games in all_games.values() for g in games]
    pd.DataFrame(all_flat).to_csv("all_predictions.csv", index=False)
    print(f"\nSaved all_predictions.csv ({len(all_flat)} total rows)")

    with open("predictions_raw.json", "w") as f:
        json.dump(all_raw, f, indent=2)
    print("Saved predictions_raw.json")


if __name__ == "__main__":
    main()