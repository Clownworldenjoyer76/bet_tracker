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
        return self.translator[self.sport].get(name, name)

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

    def _safe_read_html(self, html, season):
        try:
            tables = pd.read_html(io.StringIO(html), flavor="lxml")
            if not tables:
                raise ValueError("No tables")
            return tables
        except Exception:
            print(f"[WARN] {self.sport.upper()} season {season}: no tables found, skipping")
            return None

    def driver(self):
        df = pd.DataFrame()

        for season in self.seasons:
            url = self.base + self._make_season(season)
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)

            tables = self._safe_read_html(r.text, season)
            if tables is None:
                continue

            try:
                df = pd.concat(
                    [df, self._reformat_data(tables[0][1:], season)],
                    axis=0,
                )
            except Exception as e:
                print(f"[WARN] {self.sport.upper()} season {season}: parse failed ({e}), skipping")

        if df.empty:
            print(f"[WARN] {self.sport.upper()}: no data collected")

        return self._to_schema(df)


class NFLOddsScraper(OddsScraper):
    def __init__(self, years):
        super().__init__("nfl", years)
        self.base = "https://www.sportsbookreviewsonline.com/scoresoddsarchives/nfl-odds-"
        self.schema = {
            "season": [], "date": [], "home_team": [], "away_team": [],
            "home_final": [], "away_final": [],
            "home_close_ml": [], "away_close_ml": [],
            "open_over_under": [], "close_over_under": [],
        }

    def _reformat_data(self, df, season):
        out = pd.DataFrame()
        out["season"] = season
        out["date"] = df[0].apply(lambda x: self._make_datestr(x, season))
        out["name"] = df[3]
        out["final"] = df[8]
        out["close_ml"] = df[11]
        out["close_ou"] = df[10]
        return out

    def _to_schema(self, df):
        rows = []
        it = df.iterrows()
        next(it, None)

        for (i, r), (_, n) in self._pairwise(it):
            if i % 2 == 0:
                continue

            rows.append({
                "season": r["season"],
                "date": r["date"],
                "home_team": self._translate(n["name"]),
                "away_team": self._translate(r["name"]),
                "home_final": n["final"],
                "away_final": r["final"],
                "home_close_ml": n["close_ml"],
                "away_close_ml": r["close_ml"],
                "open_over_under": r["close_ou"],
                "close_over_under": r["close_ou"],
            })

        return pd.DataFrame(rows)


class NBAOddsScraper(NFLOddsScraper):
    def __init__(self, years):
        super().__init__(years)
        self.sport = "nba"
        self.base = "https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-"


class NHLOddsScraper(OddsScraper):
    def __init__(self, years):
        super().__init__("nhl", years)
        self.base = "https://www.sportsbookreviewsonline.com/scoresoddsarchives/nhl-odds-"
        self.schema = {
            "season": [], "date": [], "home_team": [], "away_team": [],
            "home_final": [], "away_final": [],
            "home_close_ml": [], "away_close_ml": [],
            "close_over_under": [], "close_over_under_odds": [],
        }

    def driver(self):
        df = pd.DataFrame()

        for season in self.seasons:
            season_str = self._make_season(season) if season != 2020 else "2021"
            url = self.base + season_str

            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            tables = self._safe_read_html(r.text, season)
            if tables is None:
                continue

            try:
                df = pd.concat(
                    [df, self._reformat_data(tables[0][1:], season)],
                    axis=0,
                )
            except Exception as e:
                print(f"[WARN] NHL season {season}: parse failed ({e}), skipping")

        if df.empty:
            print("[WARN] NHL: no data collected")

        return self._to_schema(df)

    def _reformat_data(self, df, season):
        out = pd.DataFrame()
        out["season"] = season
        out["date"] = df[0].apply(lambda x: self._make_datestr(x, season))
        out["name"] = df[3]
        out["final"] = df[7]
        out["close_ml"] = df[9]
        out["close_ou"] = df[14]
        out["close_ou_odds"] = df[15]
        return out

    def _to_schema(self, df):
        rows = []
        it = df.iterrows()
        next(it, None)

        for (i, r), (_, n) in self._pairwise(it):
            if i % 2 == 0:
                continue

            rows.append({
                "season": r["season"],
                "date": r["date"],
                "home_team": self._translate(n["name"]),
                "away_team": self._translate(r["name"]),
                "home_final": n["final"],
                "away_final": r["final"],
                "home_close_ml": n["close_ml"],
                "away_close_ml": r["close_ml"],
                "close_over_under": r["close_ou"],
                "close_over_under_odds": r["close_ou_odds"],
            })

        return pd.DataFrame(rows)


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
                print(f"[WARN] MLB season {season}: file unavailable, skipping")

        return df
