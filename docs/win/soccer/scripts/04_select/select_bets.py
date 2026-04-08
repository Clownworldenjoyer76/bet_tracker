#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime, UTC
import yaml

BASE = Path(__file__).resolve().parents[2]

INPUT_DIR = BASE / "03_edges"
OUTPUT_DIR = BASE / "04_select"
CONFIG_PATH = BASE.parents[3] / "config" / "soccer" / "markets.yaml"

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
def process_match(df, config):
    results = []

    for _, row in df.iterrows():
        for side in ["home", "draw", "away"]:
            rules = config[side]
            if not rules["enabled"]:
                continue

            ev = f(row.get(f"{side}_ev"))
            kelly = f(row.get(f"{side}_kelly"))
            odds = f(row.get(f"dk_{side}_decimal"))

            if not check_rules(ev, kelly, odds, rules):
                continue

            results.append({
                "market": "match_odds",
                "side": side,
                "game_id": row["game_id"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "odds": odds,
                "ev": ev,
                "kelly": kelly
            })

    return results


# =========================
# TOTALS
# =========================
def process_totals(df, config):
    results = []

    for _, row in df.iterrows():
        for side in ["over", "under"]:
            rules = config[side]
            if not rules["enabled"]:
                continue

            ev = f(row.get(f"{side}_ev"))
            kelly = f(row.get(f"{side}_kelly"))

            odds = f(row.get("dk_over25_decimal") or row.get("dk_over35_decimal")) if side == "over" else \
                   f(row.get("dk_under25_decimal") or row.get("dk_under35_decimal"))

            if not check_rules(ev, kelly, odds, rules):
                continue

            results.append({
                "market": "total",
                "side": side,
                "game_id": row["game_id"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "odds": odds,
                "ev": ev,
                "kelly": kelly
            })

    return results


# =========================
# BTTS
# =========================
def process_btts(df, config):
    results = []

    for _, row in df.iterrows():
        for side in ["yes", "no"]:
            rules = config[side]
            if not rules["enabled"]:
                continue

            ev = f(row.get(f"{side}_ev"))
            kelly = f(row.get(f"{side}_kelly"))
            odds = f(row.get(f"btts_{side}"))

            if not check_rules(ev, kelly, odds, rules):
                continue

            results.append({
                "market": "btts",
                "side": side,
                "game_id": row["game_id"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
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

    final = []

    for file in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(file)

        if "match_odds" in file.name:
            final += process_match(df, CONFIG["match_odds"])

        elif "total" in file.name:
            final += process_totals(df, CONFIG["totals"])

        elif "btts" in file.name:
            final += process_btts(df, CONFIG["btts"])

    if final:
        out = pd.DataFrame(final)
        out.to_csv(OUTPUT_DIR / "soccer_bets.csv", index=False)

    print("select bets complete")


if __name__ == "__main__":
    main()
