#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import re
import yaml

INPUT_DIR = Path("docs/win/basketball/03_edges/ev_kelly")
SELECT_DIR = Path("docs/win/basketball/04_select")
DAILY_DIR = SELECT_DIR / "daily_slate"
TOTALS_DIR = DAILY_DIR / "totals"
CONFIG_PATH = Path("docs/win/basketball/config/markets.yaml")

SELECT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

def f(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None

def in_bands(value, bands):
    if value is None:
        return False
    for low, high in bands:
        if low <= value <= high:
            return True
    return False

def detect_market(filename):
    name = filename.lower()
    if "moneyline" in name:
        return "moneyline"
    if "spread" in name:
        return "spread"
    if "total" in name:
        return "total"
    return ""

def extract_date(filename):
    m = re.search(r"\d{4}_\d{2}_\d{2}", filename)
    return m.group(0) if m else None

def market_cfg(league, market_type):
    return CONFIG["markets"][league.lower()][market_type]

def side_cfg(league, market_type, side):
    return market_cfg(league, market_type)[side]

###############################################################
# MONEYLINE
###############################################################

def moneyline(row, league):

    cfg = market_cfg(league, "moneyline")

    home_odds = f(row.get("home_dk_moneyline_american"))
    away_odds = f(row.get("away_dk_moneyline_american"))

    home_ev = f(row.get("home_ml_ev"))
    away_ev = f(row.get("away_ml_ev"))

    home_kelly = f(row.get("home_ml_kelly"))
    away_kelly = f(row.get("away_ml_kelly"))

    home_cfg = side_cfg(league, "moneyline", "home")
    away_cfg = side_cfg(league, "moneyline", "away")

    home_valid = (
        home_cfg["enabled"]
        and in_bands(home_odds, home_cfg["odds_bands"])
        and home_ev is not None and home_ev >= home_cfg["ev_min"]
        and home_kelly is not None and home_cfg["kelly_min"] <= home_kelly <= home_cfg["kelly_max"]
    )

    away_valid = (
        away_cfg["enabled"]
        and in_bands(away_odds, away_cfg["odds_bands"])
        and away_ev is not None and away_ev >= away_cfg["ev_min"]
        and away_kelly is not None and away_cfg["kelly_min"] <= away_kelly <= away_cfg["kelly_max"]
    )

    if home_valid and away_valid:
        return True, "home" if home_ev >= away_ev else "away", home_odds, max(home_ev, away_ev)

    if home_valid:
        return True, "home", home_odds, home_ev

    if away_valid:
        return True, "away", away_odds, away_ev

    return False, "", "", 0

###############################################################
# SPREAD
###############################################################

def spread(row, league):

    cfg = market_cfg(league, "spread")

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_ev = f(row.get("home_spread_ev"))
    away_ev = f(row.get("away_spread_ev"))

    home_kelly = f(row.get("home_spread_kelly"))
    away_kelly = f(row.get("away_spread_kelly"))

    home_cfg = side_cfg(league, "spread", "home")
    away_cfg = side_cfg(league, "spread", "away")

    home_valid = (
        home_cfg["enabled"]
        and in_bands(home_line, home_cfg["line_bands"])
        and home_ev is not None and home_ev >= home_cfg["ev_min"]
        and home_kelly is not None and home_cfg["kelly_min"] <= home_kelly <= home_cfg["kelly_max"]
    )

    away_valid = (
        away_cfg["enabled"]
        and in_bands(away_line, away_cfg["line_bands"])
        and away_ev is not None and away_ev >= away_cfg["ev_min"]
        and away_kelly is not None and away_cfg["kelly_min"] <= away_kelly <= away_cfg["kelly_max"]
    )

    if home_valid and away_valid:
        return True, "home" if home_ev >= away_ev else "away", home_line, max(home_ev, away_ev)

    if home_valid:
        return True, "home", home_line, home_ev

    if away_valid:
        return True, "away", away_line, away_ev

    return False, "", "", 0

###############################################################
# TOTAL
###############################################################

def total(row, league):

    cfg = market_cfg(league, "total")

    line = f(row.get("total"))

    over_ev = f(row.get("over_ev"))
    under_ev = f(row.get("under_ev"))

    over_kelly = f(row.get("over_kelly"))
    under_kelly = f(row.get("under_kelly"))

    over_cfg = side_cfg(league, "total", "over")
    under_cfg = side_cfg(league, "total", "under")

    over_valid = (
        over_cfg["enabled"]
        and in_bands(line, over_cfg["line_bands"])
        and over_ev is not None and over_ev >= over_cfg["ev_min"]
        and over_kelly is not None and over_cfg["kelly_min"] <= over_kelly <= over_cfg["kelly_max"]
    )

    under_valid = (
        under_cfg["enabled"]
        and in_bands(line, under_cfg["line_bands"])
        and under_ev is not None and under_ev >= under_cfg["ev_min"]
        and under_kelly is not None and under_cfg["kelly_min"] <= under_kelly <= under_cfg["kelly_max"]
    )

    if over_valid and under_valid:
        return True, "over" if over_ev >= under_ev else "under", line, max(over_ev, under_ev)

    if over_valid:
        return True, "over", line, over_ev

    if under_valid:
        return True, "under", line, under_ev

    return False, "", "", 0

###############################################################
# MAIN
###############################################################

def process_file(file):

    df = pd.read_csv(file)

    if df.empty:
        return None

    league = "NBA" if "nba" in file.name.lower() else "NCAAB"
    market_type = detect_market(file.name)
    game_date = extract_date(file.name)

    rows = []

    for _, row in df.iterrows():

        if market_type == "moneyline":
            ok, side, line, ev = moneyline(row, league)

        elif market_type == "spread":
            ok, side, line, ev = spread(row, league)

        else:
            ok, side, line, ev = total(row, league)

        if ok:
            r = row.to_dict()
            r["bet_side"] = side
            r["line"] = line
            r["selected_ev"] = ev
            r["market_type"] = market_type
            r["market"] = league
            r["game_date"] = game_date
            rows.append(r)

    return pd.DataFrame(rows) if rows else None

def main():

    dfs = []

    for file in sorted(INPUT_DIR.glob("*.csv")):
        df = process_file(file)
        if df is not None:
            dfs.append(df)

    if not dfs:
        print("No bets selected")
        return

    df = pd.concat(dfs, ignore_index=True)

    df.to_csv(DAILY_DIR / "nba_selected.csv", index=False)

    print("TOTAL BETS:", len(df))

if __name__ == "__main__":
    main()