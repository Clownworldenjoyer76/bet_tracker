#!/usr/bin/env python3
# docs/win/hockey/scripts/04_select/select_bets.py

import math
import pandas as pd
from pathlib import Path
from datetime import datetime, UTC
import traceback
import yaml

# =========================
# PATHS
# =========================
INPUT_DIR = Path("docs/win/hockey/03_edges/ev_kelly")
OUTPUT_DIR = Path("docs/win/hockey/04_select")
CONFIG_PATH = Path("docs/win/hockey/config/markets.yaml")

ERROR_DIR = Path("docs/win/hockey/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_CODE = "NHL"

# =========================
# LOAD CONFIG
# =========================
try:
    with open(CONFIG_PATH, "r") as f:
        _raw_config = yaml.safe_load(f)
    CONFIG = _raw_config["markets"]["nhl"]
except FileNotFoundError:
    raise SystemExit(f"Config file not found: {CONFIG_PATH}")
except yaml.YAMLError as e:
    raise SystemExit(f"Malformed YAML in {CONFIG_PATH}: {e}")
except KeyError as e:
    raise SystemExit(f"Missing expected key {e} in {CONFIG_PATH}")

# =========================
# HELPERS
# =========================
def f(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def in_range(val, ranges):
    if val is None:
        return False
    for lo, hi in ranges:
        if lo <= val <= hi:
            return True
    return False


def check_rules(ev, kelly, odds, line, rules):
    if ev is None or kelly is None:
        return False

    if ev < rules["ev_min"] or ev > rules["ev_max"]:
        return False

    if kelly < rules["kelly_min"] or kelly > rules["kelly_max"]:
        return False

    if "odds_bands" in rules:
        if not in_range(odds, rules["odds_bands"]):
            return False

    if "line_bands" in rules:
        if not in_range(line, rules["line_bands"]):
            return False

    return True


def rescale_prob(p, k=3.0):
    """
    Expand probabilities away from 0.5 using logit scaling.
    This preserves ranking but increases separation.

    Examples with k=3:
      0.45 -> ~0.35
      0.50 -> 0.50
      0.55 -> ~0.65
    """
    if p is None:
        return None

    try:
        p = float(p)
    except Exception:
        return None

    if not (0 < p < 1):
        return p

    logit = math.log(p / (1 - p))
    scaled_logit = k * logit
    return 1 / (1 + math.exp(-scaled_logit))


# =========================
# MONEYLINE
# =========================
def process_moneyline(row, config):
    results = []

    for side in ["home", "away"]:
        rules = config[side]
        if not rules["enabled"]:
            continue

        ev = f(row.get(f"{side}_ml_ev"))
        kelly = f(row.get(f"{side}_ml_kelly"))
        odds = f(row.get(f"{side}_dk_moneyline_american"))
        dec = f(row.get(f"{side}_dk_decimal_moneyline"))

        # TRUE MODEL PROB FOR THIS SIDE
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
# PUCK LINE
# =========================
def process_puck_line(row, config):
    results = []

    for side in ["home", "away"]:
        rules = config[side]
        if not rules["enabled"]:
            continue

        ev = f(row.get(f"{side}_puck_line_ev"))
        kelly = f(row.get(f"{side}_puck_line_kelly"))
        odds = f(row.get(f"{side}_dk_puck_line_american"))
        dec = f(row.get(f"{side}_dk_puck_line_decimal"))
        line = f(row.get(f"{side}_puck_line"))

        # TRUE PUCK LINE MODEL PROB FOR THIS SIDE
        raw_prob = f(row.get(f"{side}_prob_puck_line"))
        model_prob = rescale_prob(raw_prob)

        if not check_rules(ev, kelly, odds, line, rules):
            continue

        results.append({
            "market_type": "puck_line",
            "bet_side": side,
            "line": line,
            "take_bet": f"{side}_puck_line",
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
def process_total(row, config):
    results = []

    for side in ["over", "under"]:
        rules = config[side]
        if not rules["enabled"]:
            continue

        ev = f(row.get(f"{side}_ev"))
        kelly = f(row.get(f"{side}_kelly"))
        odds = f(row.get(f"dk_total_{side}_american"))
        dec = f(row.get(f"dk_total_{side}_decimal"))
        line = f(row.get("total"))

        # TRUE TOTAL MODEL PROB FOR THIS SIDE
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
    with open(ERROR_LOG, "w", encoding="utf-8") as log:
        log.write("=== NHL SELECT BETS RUN ===\n")
        log.write(f"{datetime.now(UTC).isoformat()}\n\n")

        try:
            files = sorted(INPUT_DIR.glob("*_NHL_*.csv"))
            slates = {}

            for fpath in files:
                slate_key = fpath.name.split("_NHL_")[0]
                slates.setdefault(slate_key, []).append(fpath)

            for slate_key in slates:
                final_rows = []
                seen = set()

                ml_path = INPUT_DIR / f"{slate_key}_NHL_moneyline.csv"
                pl_path = INPUT_DIR / f"{slate_key}_NHL_puck_line.csv"
                td_path = INPUT_DIR / f"{slate_key}_NHL_total.csv"

                ml_df = pd.read_csv(ml_path) if ml_path.exists() else None
                pl_df = pd.read_csv(pl_path) if pl_path.exists() else None
                td_df = pd.read_csv(td_path) if td_path.exists() else None

                if pl_df is None or pl_df.empty:
                    continue

                for _, row in pl_df.iterrows():
                    game_date = str(row.get("game_date"))
                    away = str(row.get("away_team"))
                    home = str(row.get("home_team"))
                    game_id = row.get("game_id")

                    # TOTAL
                    if td_df is not None:
                        game_tot = td_df[
                            (td_df["away_team"] == away) &
                            (td_df["home_team"] == home)
                        ]
                        for _, trow in game_tot.iterrows():
                            for t in process_total(trow, CONFIG["total"]):
                                key = f"{game_id}_{t['market_type']}_{t['bet_side']}"
                                if key not in seen:
                                    t.update({
                                        "game_date": game_date,
                                        "league": LEAGUE_CODE,
                                        "away_team": away,
                                        "home_team": home,
                                        "game_id": game_id
                                    })
                                    final_rows.append(t)
                                    seen.add(key)

                    # PUCK LINE
                    for p in process_puck_line(row, CONFIG["puck_line"]):
                        key = f"{game_id}_{p['market_type']}_{p['bet_side']}"
                        if key not in seen:
                            p.update({
                                "game_date": game_date,
                                "league": LEAGUE_CODE,
                                "away_team": away,
                                "home_team": home,
                                "game_id": game_id
                            })
                            final_rows.append(p)
                            seen.add(key)

                    # MONEYLINE
                    if ml_df is not None:
                        game_ml = ml_df[
                            (ml_df["away_team"] == away) &
                            (ml_df["home_team"] == home)
                        ]
                        for _, mrow in game_ml.iterrows():
                            for m in process_moneyline(mrow, CONFIG["moneyline"]):
                                key = f"{game_id}_{m['market_type']}_{m['bet_side']}"
                                if key not in seen:
                                    m.update({
                                        "game_date": game_date,
                                        "league": LEAGUE_CODE,
                                        "away_team": away,
                                        "home_team": home,
                                        "game_id": game_id
                                    })
                                    final_rows.append(m)
                                    seen.add(key)

                if final_rows:
                    df = pd.DataFrame(final_rows)
                    out_path = OUTPUT_DIR / f"{slate_key}_NHL.csv"
                    df.to_csv(out_path, index=False)
                    log.write(f"WROTE {out_path.name} ({len(df)} rows)\n")

        except Exception as e:
            log.write(f"ERROR: {str(e)}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()