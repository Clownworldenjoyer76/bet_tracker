# docs/win/baseball/scripts/04_select/select_bets.py

#!/usr/bin/env python3

import math
import pandas as pd
from pathlib import Path
from datetime import datetime, UTC
import traceback
import yaml

INPUT_DIR = Path("docs/win/baseball/03_edges/ev_kelly")
OUTPUT_DIR = Path("docs/win/baseball/04_select")
CONFIG_PATH = Path("docs/win/baseball/config/markets.yaml")

ERROR_DIR = Path("docs/win/baseball/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_CODE = "MLB"

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)["markets"]["mlb"]

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
    return any(lo <= val <= hi for lo, hi in ranges)

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

def check_rules(ev, kelly, odds, line, rules):
    if ev is None or kelly is None:
        return False

    if not (rules["ev_min"] <= ev <= rules["ev_max"]):
        return False

    if not (rules["kelly_min"] <= kelly <= rules["kelly_max"]):
        return False

    if "odds_bands" in rules and not in_range(odds, rules["odds_bands"]):
        return False

    if "line_bands" in rules and not in_range(line, rules["line_bands"]):
        return False

    if violates_exclude_rules(ev, kelly, odds, line, rules):
        return False

    return True

def rescale_prob(p, k=3.0):
    if p is None:
        return None
    if not (0 < p < 1):
        return p
    logit = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-k * logit))

def process_moneyline(row):
    results = []
    for side in ["home", "away"]:
        rules = CONFIG["moneyline"][side]
        if not rules["enabled"]:
            continue

        ev = f(row.get(f"{side}_ml_ev"))
        kelly = f(row.get(f"{side}_ml_kelly"))
        odds = f(row.get(f"{side}_dk_moneyline_american"))
        dec = f(row.get(f"{side}_dk_decimal_moneyline"))
        raw_prob = f(row.get(f"{side}_prob"))
        model_prob = rescale_prob(raw_prob)

        if not check_rules(ev, kelly, odds, None, rules):
            continue

        results.append({
            "market_type": "moneyline",
            "bet_side": side,
            "market": "moneyline",
            "side": side,
            "line": "",
            "take_bet": f"{side}_moneyline",
            "dk_odds_american": odds,
            "dk_odds_decimal": dec,
            "model_prob": model_prob,
            "ev": ev,
            "kelly": kelly
        })
    return results

def process_run_line(row):
    results = []
    for side in ["home", "away"]:
        rules = CONFIG["run_line"][side]
        if not rules["enabled"]:
            continue

        ev = f(row.get(f"{side}_rl_ev"))
        kelly = f(row.get(f"{side}_rl_kelly"))
        odds = f(row.get(f"{side}_dk_run_line_american"))
        dec = f(row.get(f"{side}_dk_run_line_decimal"))
        line = f(row.get(f"{side}_run_line"))
        raw_prob = f(row.get(f"{side}_prob_run_line"))

        if not check_rules(ev, kelly, odds, line, rules):
            continue

        results.append({
            "market_type": "run_line",
            "bet_side": side,
            "market": "run_line",
            "side": side,
            "line": line,
            "take_bet": f"{side}_run_line",
            "dk_odds_american": odds,
            "dk_odds_decimal": dec,
            "model_prob": raw_prob,
            "ev": ev,
            "kelly": kelly
        })
    return results

def process_total(row):
    results = []
    for side in ["over", "under"]:
        rules = CONFIG["total"][side]
        if not rules["enabled"]:
            continue

        ev = f(row.get(f"{side}_ev"))
        kelly = f(row.get(f"{side}_kelly"))
        odds = f(row.get(f"dk_total_{side}_american"))
        dec = f(row.get(f"dk_total_{side}_decimal"))
        line = f(row.get("total"))
        raw_prob = f(row.get(f"{side}_prob"))
        model_prob = rescale_prob(raw_prob)

        if not check_rules(ev, kelly, odds, line, rules):
            continue

        results.append({
            "market_type": "total",
            "bet_side": side,
            "market": "total",
            "side": side,
            "line": line,
            "take_bet": f"{side}_total",
            "dk_odds_american": odds,
            "dk_odds_decimal": dec,
            "model_prob": model_prob,
            "ev": ev,
            "kelly": kelly
        })
    return results

def main():
    with open(ERROR_LOG, "w") as log:
        try:
            files = sorted(INPUT_DIR.glob("*_mlb_*.csv"))
            for fpath in files:
                df = pd.read_csv(fpath)
                final = []

                for _, row in df.iterrows():
                    final += process_moneyline(row)
                    final += process_run_line(row)
                    final += process_total(row)

                if final:
                    pd.DataFrame(final).to_csv(OUTPUT_DIR / fpath.name, index=False)

        except Exception as e:
            log.write(f"{e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
