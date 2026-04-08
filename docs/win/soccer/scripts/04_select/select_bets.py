#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime, UTC
import yaml
import traceback

BASE = Path(__file__).resolve().parents[2]

INPUT_DIR = BASE / "03_edges"
OUTPUT_DIR = BASE / "04_select"
CONFIG_PATH = BASE / "config" / "markets.yaml"

ERROR_DIR = BASE / "errors" / "04_select"
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# LOAD CONFIG
# =========================
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)["markets"]["soccer"]


# =========================
# HELPERS
# =========================
def f(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None


def in_range(val, ranges):
    if val is None:
        return False
    for lo, hi in ranges:
        if lo <= val <= hi:
            return True
    return False


def check_rules(ev, kelly, odds, rules):
    if ev is None or kelly is None:
        return False

    if ev < rules["ev_min"] or ev > rules["ev_max"]:
        return False

    if kelly < rules["kelly_min"] or kelly > rules["kelly_max"]:
        return False

    if "odds_bands" in rules:
        if not in_range(odds, rules["odds_bands"]):
            return False

    return True


# =========================
# MATCH ODDS
# =========================
def process_match(df):
    results = []

    for _, row in df.iterrows():
        for side in ["home", "draw", "away"]:
            rules = CONFIG["match_odds"].get(side)
            if not rules or not rules.get("enabled"):
                continue

            ev = f(row.get(f"{side}_ev"))
            kelly = f(row.get(f"{side}_kelly"))
            odds = f(row.get(f"dk_{side}_decimal"))

            if not check_rules(ev, kelly, odds, rules):
                continue

            results.append({
                "game_id": row.get("game_id"),
                "sport": row.get("sport"),
                "league": row.get("league"),
                "match_date": row.get("match_date"),
                "match_time": row.get("match_time"),
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
                "market": "match_odds",
                "side": side,
                "odds": odds,
                "ev": ev,
                "kelly": kelly
            })

    return results


# =========================
# TOTALS
# =========================
def process_totals(df):
    results = []

    for _, row in df.iterrows():
        for side in ["over", "under"]:
            rules = CONFIG["totals"].get(side)
            if not rules or not rules.get("enabled"):
                continue

            ev = f(row.get(f"{side}_ev"))
            kelly = f(row.get(f"{side}_kelly"))

            if side == "over":
                odds = f(row.get("dk_over25_decimal") or row.get("dk_over35_decimal"))
            else:
                odds = f(row.get("dk_under25_decimal") or row.get("dk_under35_decimal"))

            if not check_rules(ev, kelly, odds, rules):
                continue

            results.append({
                "game_id": row.get("game_id"),
                "sport": row.get("sport"),
                "league": row.get("league"),
                "match_date": row.get("match_date"),
                "match_time": row.get("match_time"),
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
                "market": "total",
                "side": side,
                "odds": odds,
                "ev": ev,
                "kelly": kelly
            })

    return results


# =========================
# BTTS
# =========================
def process_btts(df):
    results = []

    for _, row in df.iterrows():
        for side in ["yes", "no"]:
            rules = CONFIG["btts"].get(side)
            if not rules or not rules.get("enabled"):
                continue

            ev = f(row.get(f"{side}_ev"))
            kelly = f(row.get(f"{side}_kelly"))
            odds = f(row.get(f"btts_{side}"))

            if not check_rules(ev, kelly, odds, rules):
                continue

            results.append({
                "game_id": row.get("game_id"),
                "sport": row.get("sport"),
                "league": row.get("league"),
                "match_date": row.get("match_date"),
                "match_time": row.get("match_time"),
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
                "market": "btts",
                "side": side,
                "odds": odds,
                "ev": ev,
                "kelly": kelly
            })

    return results


# =========================
# MAIN
# =========================
def main():
    with open(ERROR_LOG, "w") as log:
        log.write(f"{datetime.now(UTC).isoformat()}\n")

    all_bets = []

    try:
        for file in INPUT_DIR.glob("*.csv"):
            df = pd.read_csv(file)

            if "match_odds" in file.name:
                all_bets += process_match(df)

            elif "total" in file.name:
                all_bets += process_totals(df)

            elif "btts" in file.name:
                all_bets += process_btts(df)

        if not all_bets:
            print("no bets found")
            return

        df = pd.DataFrame(all_bets)

        # =========================
        # SPLIT BY DATE
        # =========================
        for date, group in df.groupby("match_date"):
            out_path = OUTPUT_DIR / f"{date}_soccer_bets.csv"
            group.to_csv(out_path, index=False)

        print("select bets complete")

    except Exception as e:
        with open(ERROR_LOG, "a") as log:
            log.write(f"ERROR: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
