import requests
import pandas as pd
from itertools import tee
import json
import io
from pathlib import Path


# --- resolve repo root safely ---
BASE_DIR = Path(__file__).resolve().parents[1]
TRANSLATED_PATH = BASE_DIR / "config" / "translated.json"


class OddsScraper:
    def __init__(self, sport, years):
        self.blacklist = [
            "pk",
            "PK",
            "NL",
            "nl",
            "a100",
            "a105",
            "a110",
            ".5+03",
            ".5ev",
            "-",
        ]
        self.sport = sport
        self.translator = json.load(open(TRANSLATED_PATH, "r"))
        self.seasons = years

    def _translate(self, name):
        return self.translator.get(self.sport, {}).get(name, name)

    @staticmethod
    def _make_season(season):
        season = str(season)
        yr = season[2:]
        return f"{season}-{int(yr) + 1}"

    @staticmethod
    def _make_datestr(date, season, start=8, yr_end=12):
        date = str(date)
        if len(date) == 3:
            date = f"0{date}"
        month = int(date[:2])
        day = date[2:]

        if month in range(start, yr_end + 1):
            return int(f"{season}{month:02d}{day}")
        return int(f"{int(season) + 1}{month:02d}{day}")

    @staticmethod
    def _pairwise(iterable):
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    @staticmethod
    def _safe_read_html(html, league, season):
        try:
            tables = pd.read_html(io.StringIO(html), flavor="lxml")
            if not tables:
                raise ValueError
            return tables
        except Exception:
            print(f"[WARN] {league.upper()} season {season}: no tables found, skipping")
            return None


class NFLOddsScraper(OddsScraper):
    def __init__(self, years):
        super().__init__("nfl", years)
        self.base = (
            "https://www.sportsbookreviewsonline.com/scoresoddsarchives/nfl-odds-"
        )

    def driver(self):
        df = pd.DataFrame()

        for season in self.seasons:
            url = self.base + self._make_season(season)
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)

            tables = self._safe_read_html(r.text, "nfl", season)
            if tables is None:
                continue

            try:
                tmp = tables[0][1:]
                tmp["season"] = season
                df = pd.concat([df, tmp], axis=0)
            except Exception as e:
                print(f"[WARN] NFL season {season}: parse failed ({e})")

        return df


class NBAOddsScraper(NFLOddsScraper):
    def __init__(self, years):
        super().__init__(years)
        self.sport = "nba"
        self.base = (
            "https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-"
        )


class NHLOddsScraper(OddsScraper):
    def __init__(self, years):
        super().__init__("nhl", years)
        self.base = (
            "https://www.sportsbookreviewsonline.com/scoresoddsarchives/nhl-odds-"
        )

    def driver(self):
        df = pd.DataFrame()

        for season in self.seasons:
            season_str = self._make_season(season) if season != 2020 else "2021"
            url = self.base + season_str
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)

            tables = self._safe_read_html(r.text, "nhl", season)
            if tables is None:
                continue

            try:
                tmp = tables[0][1:]
                tmp["season"] = season
                df = pd.concat([df, tmp], axis=0)
            except Exception as e:
                print(f"[WARN] NHL season {season}: parse failed ({e})")

        return df


class MLBOddsScraper(OddsScraper):
    def __init__(self, years):
        super().__init__("mlb", years)
        self.base = (
            "https://www.sportsbookreviewsonline.com/wp-content/uploads/"
            "sportsbookreviewsonline_com_737/mlb-odds-"
        )
        self.ext = ".xlsx"

    def driver(self):
        df = pd.DataFrame()

        for season in self.seasons:
            url = self.base + str(season) + self.ext
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                with io.BytesIO(r.content) as fh:
                    sheets = pd.read_excel(fh, sheet_name=None)
                df = pd.concat([df, sheets["Sheet1"][1:]], axis=0)
            except Exception:
                print(f"[WARN] MLB season {season}: unavailable")

        return df
