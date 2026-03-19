#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import re
import yaml
from collections import defaultdict

INPUT_DIR = Path("docs/win/basketball/03_edges/ev_kelly")
SELECT_DIR = Path("docs/win/basketball/04_select")
DAILY_DIR = SELECT_DIR / "daily_slate"
CONFIG_PATH = Path("docs/win/basketball/config/markets.yaml")

SELECT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

###############################################################
# DEBUG COUNTERS
###############################################################

DEBUG = defaultdict(int)

def count(key):
    DEBUG[key] += 1

###############################################################
# HELPERS
###############################################################

def f(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None

def in_bands(value, bands):
    if value is None:
        count("fail_null")
        return False
    ok = any(low <= value <= high for low, high in bands)
    if not ok:
        count("fail_band")
    return ok

def detect_market(filename):
    name = filename.lower()

    # 🔴 FIX: correct ordering (ncaab first)
    if "ncaab" in name:
        return "NCAAB"
    elif "nba" in name:
        return "NBA"
    else:
        raise ValueError(f"Unknown market in filename: {filename}")

def detect_market_type(filename):
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

def market_cfg(market, market_type):
    return CONFIG["markets"][market.lower()][market_type]

def ev_ok(ev, cfg):
    if ev is None:
        count("fail_null")
        return False
    if ev < cfg["ev_min"]:
        count("fail_ev_min")
        return False
    if ev > cfg.get("ev_max", float("inf")):
        count("fail_ev_max")
        return False
    return True

def kelly_ok(kelly, cfg):
    if kelly is None:
        count("fail_null")
        return False
    if not (cfg["kelly_min"] <= kelly <= cfg["kelly_max"]):
        count("fail_kelly")
        return False
    return True

def pick_side(valid_sides, preference):
    if not valid_sides:
        return None

    if preference == "best_kelly":
        return max(valid_sides, key=lambda x: x["kelly"])

    return max(valid_sides, key=lambda x: x["ev"])

###############################################################
# MARKET LOGIC
###############################################################

def moneyline(row, market):
    cfg = market_cfg(market, "moneyline")

    if not cfg.get("enabled", True):
        return False, "", "", 0

    pref = cfg.get("pick_preference", "best_ev")

    sides = []

    for side in ["home", "away"]:
        scfg = cfg[side]

        if not scfg.get("enabled", True):
            continue

        odds = f(row.get(f"{side}_dk_moneyline_american"))
        ev = f(row.get(f"{side}_ml_ev"))
        kelly = f(row.get(f"{side}_ml_kelly"))

        if (
            in_bands(odds, scfg["odds_bands"])
            and ev_ok(ev, scfg)
            and kelly_ok(kelly, scfg)
        ):
            sides.append({
                "side": side,
                "line": odds,
                "ev": ev,
                "kelly": kelly
            })

    pick = pick_side(sides, pref)

    if pick:
        return True, pick["side"], pick["line"], pick["ev"]

    return False, "", "", 0


def spread(row, market):
    cfg = market_cfg(market, "spread")

    if not cfg.get("enabled", True):
        return False, "", "", 0

    pref = cfg.get("pick_preference", "best_ev")

    sides = []

    for side in ["home", "away"]:
        scfg = cfg[side]

        if not scfg.get("enabled", True):
            continue

        line = f(row.get(f"{side}_spread"))
        ev = f(row.get(f"{side}_spread_ev"))
        kelly = f(row.get(f"{side}_spread_kelly"))

        if (
            in_bands(line, scfg["line_bands"])
            and ev_ok(ev, scfg)
            and kelly_ok(kelly, scfg)
        ):
            sides.append({
                "side": side,
                "line": line,
                "ev": ev,
                "kelly": kelly
            })

    pick = pick_side(sides, pref)

    if pick:
        return True, pick["side"], pick["line"], pick["ev"]

    return False, "", "", 0


def total(row, market):
    cfg = market_cfg(market, "total")

    if not cfg.get("enabled", True):
        return False, "", "", 0

    pref = cfg.get("pick_preference", "best_ev")

    line = f(row.get("total"))

    sides = []

    for side in ["over", "under"]:
        scfg = cfg[side]

        if not scfg.get("enabled", True):
            continue

        ev = f(row.get(f"{side}_ev"))
        kelly = f(row.get(f"{side}_kelly"))

        if (
            in_bands(line, scfg["line_bands"])
            and ev_ok(ev, scfg)
            and kelly_ok(kelly, scfg)
        ):
            sides.append({
                "side": side,
                "line": line,
                "ev": ev,
                "kelly": kelly
            })

    pick = pick_side(sides, pref)

    if pick:
        return True, pick["side"], pick["line"], pick["ev"]

    return False, "", "", 0

###############################################################
# PROCESS FILE
###############################################################

def process_file(file):

    df = pd.read_csv(file)

    if df.empty:
        print(f"⚠️ EMPTY FILE: {file.name}")
        return pd.DataFrame()

    market = detect_market(file.name)
    market_type = detect_market_type(file.name)
    game_date = extract_date(file.name)

    print(f"\nProcessing {file.name} -> {market} | rows: {len(df)}")

    rows = []

    for _, row in df.iterrows():

        if market_type == "moneyline":
            ok, side, line, ev = moneyline(row, market)
        elif market_type == "spread":
            ok, side, line, ev = spread(row, market)
        else:
            ok, side, line, ev = total(row, market)

        if ok:
            count("selected")

            r = row.to_dict()
            r["bet_side"] = side
            r["line"] = line
            r["selected_ev"] = ev
            r["market_type"] = market_type
            r["market"] = market
            r["league"] = "basketball"   # ← your structure
            r["game_date"] = game_date
            rows.append(r)
        else:
            count("rejected")

    print(f"Selected: {len(rows)}")

    return pd.DataFrame(rows)

###############################################################
# MAIN
###############################################################

def main():

    dfs = []

    for file in sorted(INPUT_DIR.glob("*.csv")):
        dfs.append(process_file(file))

    final_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if final_df.empty:
        print("⚠️ No selections generated")
        return

    print("\n--- MARKET COUNTS ---")
    print(final_df["market"].value_counts())

    ###########################################################
    # 🔴 FIX: SPLIT OUTPUTS
    ###########################################################

    nba_df = final_df[final_df["market"] == "NBA"]
    ncaab_df = final_df[final_df["market"] == "NCAAB"]

    nba_path = DAILY_DIR / "nba_selected.csv"
    ncaab_path = DAILY_DIR / "ncaab_selected.csv"

    nba_df.to_csv(nba_path, index=False)
    ncaab_df.to_csv(ncaab_path, index=False)

    ###########################################################
    # DEBUG
    ###########################################################

    print("\n--- DEBUG COUNTS ---")
    for k, v in sorted(DEBUG.items()):
        print(f"{k}: {v}")

    print("\n========================")
    print(f"NBA rows: {len(nba_df)} -> {nba_path}")
    print(f"NCAAB rows: {len(ncaab_df)} -> {ncaab_path}")
    print("========================")


if __name__ == "__main__":
    main()
