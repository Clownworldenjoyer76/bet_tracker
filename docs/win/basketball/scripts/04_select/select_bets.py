# docs/win/basketball/scripts/04_select/select_bets.py

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

DEBUG = defaultdict(int)

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
    return any(low <= value <= high for low, high in bands)

def violates_exclude_rules(ev, kelly, odds, line, rules):
    for r in rules.get("exclude_rules", []):
        if "ev_min" in r and (ev is None or ev < r["ev_min"]):
            continue
        if "ev_max" in r and (ev is None or ev > r["ev_max"]):
            continue
        if "odds_min" in r and (odds is None or odds < r["odds_min"]):
            continue
        if "odds_max" in r and (odds is None or odds > r["odds_max"]):
            continue
        if "line_min" in r and (line is None or line < r["line_min"]):
            continue
        if "line_max" in r and (line is None or line > r["line_max"]):
            continue
        return True
    return False

def ev_ok(ev, cfg):
    return ev is not None and cfg["ev_min"] <= ev <= cfg.get("ev_max", float("inf"))

def kelly_ok(kelly, cfg):
    return kelly is not None and cfg["kelly_min"] <= kelly <= cfg["kelly_max"]

def pick_side(valid_sides, preference):
    if not valid_sides:
        return None
    return max(valid_sides, key=lambda x: x["ev"] if preference != "best_kelly" else x["kelly"])

def moneyline(row, market):
    cfg = CONFIG["markets"][market.lower()]["moneyline"]
    pref = cfg.get("pick_preference", "best_ev")

    sides = []
    for side in ["home", "away"]:
        scfg = cfg[side]
        odds = f(row.get(f"{side}_dk_moneyline_american"))
        ev = f(row.get(f"{side}_ml_ev"))
        kelly = f(row.get(f"{side}_ml_kelly"))

        if (
            in_bands(odds, scfg["odds_bands"])
            and ev_ok(ev, scfg)
            and kelly_ok(kelly, scfg)
            and not violates_exclude_rules(ev, kelly, odds, None, scfg)
        ):
            sides.append({"side": side, "line": odds, "ev": ev, "kelly": kelly})

    pick = pick_side(sides, pref)
    return (True, pick["side"], pick["line"], pick["ev"]) if pick else (False, "", "", 0)

def spread(row, market):
    cfg = CONFIG["markets"][market.lower()]["spread"]
    pref = cfg.get("pick_preference", "best_ev")

    sides = []
    for side in ["home", "away"]:
        scfg = cfg[side]
        line = f(row.get(f"{side}_spread"))
        ev = f(row.get(f"{side}_spread_ev"))
        kelly = f(row.get(f"{side}_spread_kelly"))

        if (
            in_bands(line, scfg["line_bands"])
            and ev_ok(ev, scfg)
            and kelly_ok(kelly, scfg)
            and not violates_exclude_rules(ev, kelly, None, line, scfg)
        ):
            sides.append({"side": side, "line": line, "ev": ev, "kelly": kelly})

    pick = pick_side(sides, pref)
    return (True, pick["side"], pick["line"], pick["ev"]) if pick else (False, "", "", 0)

def total(row, market):
    cfg = CONFIG["markets"][market.lower()]["total"]
    pref = cfg.get("pick_preference", "best_ev")
    line = f(row.get("total"))

    sides = []
    for side in ["over", "under"]:
        scfg = cfg[side]
        ev = f(row.get(f"{side}_ev"))
        kelly = f(row.get(f"{side}_kelly"))

        if (
            in_bands(line, scfg["line_bands"])
            and ev_ok(ev, scfg)
            and kelly_ok(kelly, scfg)
            and not violates_exclude_rules(ev, kelly, None, line, scfg)
        ):
            sides.append({"side": side, "line": line, "ev": ev, "kelly": kelly})

    pick = pick_side(sides, pref)
    return (True, pick["side"], pick["line"], pick["ev"]) if pick else (False, "", "", 0)

def main():
    dfs = []
    for file in sorted(INPUT_DIR.glob("*.csv")):
        df = pd.read_csv(file)
        rows = []

        market = "NBA" if "nba" in file.name.lower() else "NCAAB"
        mtype = "moneyline" if "moneyline" in file.name else "spread" if "spread" in file.name else "total"

        for _, row in df.iterrows():
            if mtype == "moneyline":
                ok, side, line, ev = moneyline(row, market)
            elif mtype == "spread":
                ok, side, line, ev = spread(row, market)
            else:
                ok, side, line, ev = total(row, market)

            if ok:
                r = row.to_dict()
                r.update({"bet_side": side, "line": line, "selected_ev": ev})
                rows.append(r)

        if rows:
            dfs.append(pd.DataFrame(rows))

    if dfs:
        final = pd.concat(dfs, ignore_index=True)
        final.to_csv(DAILY_DIR / "combined.csv", index=False)

if __name__ == "__main__":
    main()
