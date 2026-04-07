# docs/win/baseball/scripts/04_select/select_bets.py
#!/usr/bin/env python3

import math
import pandas as pd
from pathlib import Path
from datetime import datetime, UTC
import traceback
import yaml

# =========================
# CONFIG
# =========================

INPUT_DIR   = Path("docs/win/baseball/03_edges/ev_kelly")
OUTPUT_DIR  = Path("docs/win/baseball/04_select")
CONFIG_PATH = Path("docs/win/baseball/config/markets.yaml")

ERROR_DIR = Path("docs/win/baseball/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

DEBUG = True

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
        best = max(candidates, key=lambda x: (x["model_prob"] or 0))
        if DEBUG:
            print(f"[SELECT best_prob] {best['side']} prob={best['model_prob']} ev={best['ev']}")
        return [best]

    best = max(candidates, key=lambda x: (x["ev"] or 0))
    if DEBUG:
        print(f"[SELECT best_ev] {best['side']} ev={best['ev']} prob={best['model_prob']}")
    return [best]

# =========================
# PROCESS RUN LINE
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
        prob  = f(row.get(f"{side}_run_line_prob"))  # FIXED

        if not check_rules(ev, kelly, odds, line, prob, rules, counters["run_line"][side]):
            continue

        candidates.append({
            "market_type": "run_line",
            "bet_side": side,
            "side": side,
            "line": line,
            "take_bet": f"{side}_run_line",
            "dk_odds_american": odds,
            "dk_odds_decimal": dec,
            "model_prob": prob,
            "ev": ev,
            "kelly": kelly,
        })

    pref = CONFIG["run_line"].get("pick_preference", "best_ev")
    return select_candidate(candidates, pref)

# =========================
# MAIN
# =========================

def main():
    with open(ERROR_LOG, "w") as log:
        try:
            log.write(f"=== RUN {datetime.now(UTC)} ===\n")

            files = sorted(INPUT_DIR.glob("*_mlb_run_line.csv"))
            if not files:
                log.write("No files\n")
                return

            counters = {
                "run_line": {
                    "home": {"passed":0,"ev_fail":0,"kelly_fail":0,"odds_fail":0,"line_fail":0,"missing":0},
                    "away": {"passed":0,"ev_fail":0,"kelly_fail":0,"odds_fail":0,"line_fail":0,"missing":0},
                }
            }

            final = []

            for fp in files:
                df = pd.read_csv(fp)

                for _, row in df.iterrows():
                    base = {
                        "game_id": row["game_id"],
                        "game_date": row["game_date"],
                        "league": LEAGUE_CODE,
                        "away_team": row["away_team"],
                        "home_team": row["home_team"],
                    }

                    for r in process_run_line(row, counters):
                        final.append({**base, **r})

            if final:
                out = OUTPUT_DIR / "selected_run_line.csv"
                pd.DataFrame(final).to_csv(out, index=False)
                log.write(f"Wrote {len(final)} bets\n")

            log.write("\n=== COUNTERS ===\n")
            for side in counters["run_line"]:
                log.write(f"{side}: {counters['run_line'][side]}\n")

        except Exception as e:
            log.write(f"ERROR: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
