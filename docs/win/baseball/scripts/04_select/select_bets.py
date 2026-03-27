#!/usr/bin/env python3

import math
import pandas as pd
from pathlib import Path
from datetime import datetime, UTC
import traceback
import yaml

# =========================
# PATHS
# =========================
INPUT_DIR = Path("docs/win/baseball/03_edges/ev_kelly")
OUTPUT_DIR = Path("docs/win/baseball/04_select")
CONFIG_PATH = Path("docs/win/baseball/config/markets.yaml")

ERROR_DIR = Path("docs/win/baseball/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_CODE = "MLB"

# =========================
# LOAD CONFIG
# =========================
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

    return True


def rescale_prob(p, k=3.0):
    if p is None:
        return None
    if not (0 < p < 1):
        return p

    logit = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-k * logit))


# =========================
# MONEYLINE
# =========================
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
            "line": "",
            "take_bet": f"{side}_moneyline",
            "dk_odds_american": odds,
            "dk_odds_decimal": dec,
            "model_prob": model_prob,
            "ev": ev,
            "kelly": kelly
        })

    return results


# =========================
# RUN LINE
# =========================
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
        model_prob = rescale_prob(raw_prob)

        if not check_rules(ev, kelly, odds, line, rules):
            continue

        results.append({
            "market_type": "run_line",
            "bet_side": side,
            "line": line,
            "take_bet": f"{side}_run_line",
            "dk_odds_american": odds,
            "dk_odds_decimal": dec,
            "model_prob": model_prob,
            "ev": ev,
            "kelly": kelly
        })

    return results


# =========================
# TOTAL
# =========================
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
            "line": line,
            "take_bet": f"{side}_total",
            "dk_odds_american": odds,
            "dk_odds_decimal": dec,
            "model_prob": model_prob,
            "ev": ev,
            "kelly": kelly
        })

    return results


# =========================
# MAIN
# =========================
def main():
    with open(ERROR_LOG, "w") as log:
        log.write("=== MLB SELECT BETS ===\n")

        try:
            files = sorted(INPUT_DIR.glob("*_mlb_*.csv"))
            slates = {}

            for f in files:
                key = f.name.split("_mlb_")[0]
                slates.setdefault(key, []).append(f)

            for slate in slates:
                final = []
                seen = set()

                ml = INPUT_DIR / f"{slate}_mlb_moneyline.csv"
                rl = INPUT_DIR / f"{slate}_mlb_run_line.csv"
                tt = INPUT_DIR / f"{slate}_mlb_total.csv"

                ml_df = pd.read_csv(ml) if ml.exists() else None
                rl_df = pd.read_csv(rl) if rl.exists() else None
                tt_df = pd.read_csv(tt) if tt.exists() else None

                if rl_df is None or rl_df.empty:
                    continue

                for _, row in rl_df.iterrows():
                    game_id = row["game_id"]
                    game_date = row["game_date"]
                    away = row["away_team"]
                    home = row["home_team"]

                    # TOTAL
                    if tt_df is not None:
                        match = tt_df[
                            (tt_df["away_team"] == away) &
                            (tt_df["home_team"] == home)
                        ]
                        for _, t in match.iterrows():
                            for r in process_total(t):
                                key = f"{game_id}_{r['market_type']}_{r['bet_side']}"
                                if key not in seen:
                                    r.update({
                                        "game_id": game_id,
                                        "game_date": game_date,
                                        "league": LEAGUE_CODE,
                                        "away_team": away,
                                        "home_team": home
                                    })
                                    final.append(r)
                                    seen.add(key)

                    # RUN LINE
                    for r in process_run_line(row):
                        key = f"{game_id}_{r['market_type']}_{r['bet_side']}"
                        if key not in seen:
                            r.update({
                                "game_id": game_id,
                                "game_date": game_date,
                                "league": LEAGUE_CODE,
                                "away_team": away,
                                "home_team": home
                            })
                            final.append(r)
                            seen.add(key)

                    # MONEYLINE
                    if ml_df is not None:
                        match = ml_df[
                            (ml_df["away_team"] == away) &
                            (ml_df["home_team"] == home)
                        ]
                        for _, m in match.iterrows():
                            for r in process_moneyline(m):
                                key = f"{game_id}_{r['market_type']}_{r['bet_side']}"
                                if key not in seen:
                                    r.update({
                                        "game_id": game_id,
                                        "game_date": game_date,
                                        "league": LEAGUE_CODE,
                                        "away_team": away,
                                        "home_team": home
                                    })
                                    final.append(r)
                                    seen.add(key)

                if final:
                    df = pd.DataFrame(final)
                    out = OUTPUT_DIR / f"{slate}_MLB.csv"
                    df.to_csv(out, index=False)

        except Exception as e:
            log.write(f"ERROR: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
