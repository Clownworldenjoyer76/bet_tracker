#!/usr/bin/env python3

import math
import pandas as pd
from pathlib import Path
from datetime import datetime, UTC
import traceback
import yaml

INPUT_DIR   = Path("docs/win/baseball/03_edges/ev_kelly")
OUTPUT_DIR  = Path("docs/win/baseball/04_select")
CONFIG_PATH = Path("docs/win/baseball/config/markets.yaml")

ERROR_DIR = Path("docs/win/baseball/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_CODE = "MLB"

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)["markets"]["mlb"]

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
    return any(lo <= val <= hi for lo, hi in ranges)

def rescale_prob(p, k=3.0):
    if p is None or not (0 < p < 1):
        return p
    logit = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-k * logit))

def check_rules(ev, kelly, odds, line, prob, rules, counters):
    if ev is None or kelly is None:
        counters["missing"] += 1
        return False

    if not (rules["ev_min"] <= ev <= rules["ev_max"]):
        counters["ev_fail"] += 1
        return False

    if not (rules["kelly_min"] <= kelly <= rules["kelly_max"]):
        counters["kelly_fail"] += 1
        return False

    if "odds_bands" in rules and not in_range(odds, rules["odds_bands"]):
        counters["odds_fail"] += 1
        return False

    if "line_bands" in rules and not in_range(line, rules["line_bands"]):
        counters["line_fail"] += 1
        return False

    if "prob_min" in rules and prob is not None and prob < rules["prob_min"]:
        counters.setdefault("prob_fail", 0)
        counters["prob_fail"] += 1
        return False

    counters["passed"] += 1
    return True

def select_candidate(candidates, preference):
    if not candidates:
        return []

    if preference == "all":
        return candidates

    if preference == "best_prob":
        return [max(candidates, key=lambda x: (x["model_prob"] or 0))]

    # default = best_ev
    return [max(candidates, key=lambda x: (x["ev"] or 0))]

# =========================
# PROCESSORS
# =========================

def process_run_line(row, counters):
    candidates = []

    for side in ["home", "away"]:
        rules = CONFIG["run_line"][side]
        if not rules["enabled"]:
            continue

        ev    = f(row.get(f"{side}_rl_ev"))
        kelly = f(row.get(f"{side}_rl_kelly"))
        odds  = f(row.get(f"{side}_dk_run_line_american"))
        dec   = f(row.get(f"{side}_dk_run_line_decimal"))
        line  = f(row.get(f"{side}_run_line"))

        # ✅ FIXED COLUMN NAME
        raw_prob = f(row.get(f"{side}_run_line_prob"))

        if not check_rules(ev, kelly, odds, line, raw_prob, rules, counters["run_line"][side]):
            continue

        candidates.append({
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
            "kelly": kelly,
        })

    preference = CONFIG["run_line"].get("pick_preference", "best_ev")
    return select_candidate(candidates, preference)

def process_moneyline(row, counters):
    candidates = []

    for side in ["home", "away"]:
        rules = CONFIG["moneyline"][side]
        if not rules["enabled"]:
            continue

        ev    = f(row.get(f"{side}_ml_ev"))
        kelly = f(row.get(f"{side}_ml_kelly"))
        odds  = f(row.get(f"{side}_dk_moneyline_american"))
        dec   = f(row.get(f"{side}_dk_decimal_moneyline"))
        raw_prob = f(row.get(f"{side}_prob"))
        model_prob = rescale_prob(raw_prob)

        if not check_rules(ev, kelly, odds, None, model_prob, rules, counters["moneyline"][side]):
            continue

        candidates.append({
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
            "kelly": kelly,
        })

    preference = CONFIG["moneyline"].get("pick_preference", "best_ev")
    return select_candidate(candidates, preference)

def process_total(row, counters):
    candidates = []

    for side in ["over", "under"]:
        rules = CONFIG["total"][side]
        if not rules["enabled"]:
            continue

        ev    = f(row.get(f"{side}_ev"))
        kelly = f(row.get(f"{side}_kelly"))
        odds  = f(row.get(f"dk_total_{side}_american"))
        dec   = f(row.get(f"dk_total_{side}_decimal"))
        line  = f(row.get("total"))
        raw_prob = f(row.get(f"{side}_prob"))
        model_prob = rescale_prob(raw_prob)

        if not check_rules(ev, kelly, odds, line, model_prob, rules, counters["total"][side]):
            continue

        candidates.append({
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
            "kelly": kelly,
        })

    preference = CONFIG["total"].get("pick_preference", "best_ev")
    return select_candidate(candidates, preference)

# =========================
# MAIN
# =========================

def main():
    with open(ERROR_LOG, "w") as log:
        try:
            log.write(f"=== SELECT BETS RUN {datetime.now(UTC)} ===\n")

            files = sorted(INPUT_DIR.glob("*_mlb_*.csv"))
            if not files:
                log.write("ERROR: No input files found\n")
                return

            slates = {}
            for fp in files:
                key = fp.name.split("_mlb_")[0]
                slates.setdefault(key, []).append(fp)

            for slate in slates:
                ml_path = INPUT_DIR / f"{slate}_mlb_moneyline.csv"
                rl_path = INPUT_DIR / f"{slate}_mlb_run_line.csv"
                tt_path = INPUT_DIR / f"{slate}_mlb_total.csv"

                ml_df = pd.read_csv(ml_path) if ml_path.exists() else None
                rl_df = pd.read_csv(rl_path) if rl_path.exists() else None
                tt_df = pd.read_csv(tt_path) if tt_path.exists() else None

                if rl_df is None or rl_df.empty:
                    continue

                counters = {
                    "moneyline": {"home": {}, "away": {}},
                    "run_line": {"home": {}, "away": {}},
                    "total": {"over": {}, "under": {}},
                }

                final = []
                seen = set()

                for _, row in rl_df.iterrows():
                    base = {
                        "game_id": row["game_id"],
                        "game_date": row["game_date"],
                        "league": LEAGUE_CODE,
                        "away_team": row["away_team"],
                        "home_team": row["home_team"],
                    }

                    for r in process_run_line(row, counters):
                        k = f"{row['game_id']}_{r['market_type']}_{r['bet_side']}"
                        if k not in seen:
                            final.append({**base, **r})
                            seen.add(k)

                if final:
                    out = OUTPUT_DIR / f"{slate}_MLB.csv"
                    pd.DataFrame(final).to_csv(out, index=False)

        except Exception as e:
            log.write(f"\nFATAL ERROR:\n{e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
