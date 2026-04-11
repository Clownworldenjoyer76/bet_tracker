#!/usr/bin/env python3
# docs/win/baseball/scripts/04_select/baseball_select_bets.py

import math
import traceback
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd
import yaml

INPUT_DIR   = Path("docs/win/baseball/03_edges/ev_kelly")
OUTPUT_DIR  = Path("docs/win/baseball/04_select")
CONFIG_PATH = Path("docs/win/baseball/config/markets.yaml")

ERROR_DIR = Path("docs/win/baseball/errors/04_select")
LOG_FILE  = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_CODE = "MLB"

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)["markets"]["mlb"]


# =========================
# LOGGING
# =========================

def _now():
    return datetime.now(UTC).isoformat()


def _log(msg: str, level: str = "INFO"):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{_now()} | {level:<5} | {msg.rstrip()}\n")


def _write_summary(summary: dict, per_slate: list) -> None:
    lines = [
        "",
        "=" * 60,
        f"SUMMARY  {_now()}",
        "=" * 60,
        f"  slates_found    : {summary['slates_found']}",
        f"  slates_written  : {summary['slates_written']}",
        f"  total_bets      : {summary['total_bets']}",
        f"  moneyline_bets  : {summary['moneyline_bets']}",
        f"  run_line_bets   : {summary['run_line_bets']}",
        f"  total_mkt_bets  : {summary['total_mkt_bets']}",
        f"  skipped_slates  : {summary['skipped_slates']}",
        f"  errors          : {summary['errors']}",
        "",
        "--- Filter Breakdown ---",
    ]
    for market, sides in summary.get("counters", {}).items():
        for side, c in sides.items():
            lines.append(
                f"  {market}-{side:<10} passed={c['passed']:>4} "
                f"ev_fail={c['ev_fail']:>4} kelly_fail={c['kelly_fail']:>4} "
                f"odds_fail={c['odds_fail']:>4} line_fail={c['line_fail']:>4} "
                f"missing={c['missing']:>4} excluded={c['excluded']:>4}"
            )
    lines += [
        "",
        f"  {'slate':<30} {'bets':>5} {'ml':>5} {'rl':>5} {'tot':>5} {'status':>10}",
    ]
    for ps in per_slate:
        lines.append(
            f"  {ps['slate']:<30} {ps['bets']:>5} {ps['ml']:>5} "
            f"{ps['rl']:>5} {ps['tot']:>5} {ps['status']:>10}"
        )
    status = "SUCCESS" if summary["errors"] == 0 else "COMPLETED WITH ERRORS"
    lines += ["", f"STATUS: {status}", "=" * 60]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# =========================
# HELPERS
# =========================

def fv(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def in_range(val, ranges):
    if val is None:
        return False
    return any(lo <= val <= hi for lo, hi in ranges)


def rescale_prob(p, k=3.0):
    if p is None:
        return None
    if not (0 < p < 1):
        return p
    logit = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-k * logit))


def violates_exclude_rules(ev, kelly, odds, line, prob, rules):
    for r in rules.get("exclude_rules", []):
        if "ev_min"    in r and (ev    is None or ev    < r["ev_min"]):    continue
        if "ev_max"    in r and (ev    is None or ev    > r["ev_max"]):    continue
        if "kelly_min" in r and (kelly is None or kelly < r["kelly_min"]): continue
        if "kelly_max" in r and (kelly is None or kelly > r["kelly_max"]): continue
        if "odds_min"  in r and (odds  is None or odds  < r["odds_min"]):  continue
        if "odds_max"  in r and (odds  is None or odds  > r["odds_max"]):  continue
        if "line_min"  in r and (line  is None or line  < r["line_min"]):  continue
        if "line_max"  in r and (line  is None or line  > r["line_max"]):  continue
        if "prob_min"  in r and (prob  is None or prob  < r["prob_min"]):  continue
        if "prob_max"  in r and (prob  is None or prob  > r["prob_max"]):  continue
        return True
    return False


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
    if "odds_bands" in rules:
        if odds is None:
            counters["odds_fail"] += 1
            return False
        if not in_range(odds, rules["odds_bands"]):
            counters["odds_fail"] += 1
            return False
    if "line_bands" in rules:
        if line is None:
            counters["line_fail"] += 1
            return False
        if not in_range(line, rules["line_bands"]):
            counters["line_fail"] += 1
            return False
    if "prob_min" in rules and (prob is None or prob < rules["prob_min"]):
        counters["prob_fail"] = counters.get("prob_fail", 0) + 1
        return False
    if "prob_max" in rules and (prob is None or prob > rules["prob_max"]):
        counters["prob_fail"] = counters.get("prob_fail", 0) + 1
        return False
    if violates_exclude_rules(ev, kelly, odds, line, prob, rules):
        counters["excluded"] += 1
        return False
    counters["passed"] += 1
    return True


def init_counter():
    return {"passed": 0, "ev_fail": 0, "kelly_fail": 0, "odds_fail": 0,
            "line_fail": 0, "prob_fail": 0, "excluded": 0, "missing": 0}


def select_candidate(candidates, preference, market_name=None, game_id=None):
    if not candidates:
        return []
    if preference == "all":
        return candidates
    if preference == "best_prob":
        return [max(candidates, key=lambda x: x["model_prob"] or -999)]
    return [max(candidates, key=lambda x: x["ev"] or -999)]


# =========================
# MARKET PROCESSORS
# =========================

def process_moneyline(row, counters):
    candidates = []
    for side in ["home", "away"]:
        rules = CONFIG["moneyline"][side]
        if not rules["enabled"]:
            continue
        ev         = fv(row.get(f"{side}_ml_ev"))
        kelly      = fv(row.get(f"{side}_ml_kelly"))
        odds       = fv(row.get(f"{side}_dk_moneyline_american"))
        dec        = fv(row.get(f"{side}_dk_decimal_moneyline"))
        model_prob = rescale_prob(fv(row.get(f"{side}_prob")))
        if not check_rules(ev, kelly, odds, None, model_prob, rules, counters["moneyline"][side]):
            continue
        candidates.append({
            "market_type": "moneyline", "bet_side": side, "market": "moneyline",
            "side": side, "line": "", "take_bet": f"{side}_moneyline",
            "dk_odds_american": odds, "dk_odds_decimal": dec,
            "model_prob": model_prob, "ev": ev, "kelly": kelly,
        })
    return select_candidate(candidates,
                            CONFIG["moneyline"].get("pick_preference", "best_ev"),
                            "moneyline", row.get("game_id"))


def process_run_line(row, counters):
    candidates = []
    for side in ["home", "away"]:
        rules = CONFIG["run_line"][side]
        if not rules["enabled"]:
            continue
        ev       = fv(row.get(f"{side}_rl_ev"))
        kelly    = fv(row.get(f"{side}_rl_kelly"))
        odds     = fv(row.get(f"{side}_dk_run_line_american"))
        dec      = fv(row.get(f"{side}_dk_run_line_decimal"))
        line     = fv(row.get(f"{side}_run_line"))
        raw_prob = fv(row.get(f"{side}_run_line_prob"))
        if not check_rules(ev, kelly, odds, line, raw_prob, rules, counters["run_line"][side]):
            continue
        candidates.append({
            "market_type": "run_line", "bet_side": side, "market": "run_line",
            "side": side, "line": line, "take_bet": f"{side}_run_line",
            "dk_odds_american": odds, "dk_odds_decimal": dec,
            "model_prob": raw_prob, "ev": ev, "kelly": kelly,
        })
    return select_candidate(candidates,
                            CONFIG["run_line"].get("pick_preference", "best_ev"),
                            "run_line", row.get("game_id"))


def process_total(row, counters):
    candidates = []
    for side in ["over", "under"]:
        rules = CONFIG["total"][side]
        if not rules["enabled"]:
            continue
        ev         = fv(row.get(f"{side}_ev"))
        kelly      = fv(row.get(f"{side}_kelly"))
        odds       = fv(row.get(f"dk_total_{side}_american"))
        dec        = fv(row.get(f"dk_total_{side}_decimal"))
        line       = fv(row.get("total"))
        model_prob = rescale_prob(fv(row.get(f"{side}_prob")))
        if not check_rules(ev, kelly, odds, line, model_prob, rules, counters["total"][side]):
            continue
        candidates.append({
            "market_type": "total", "bet_side": side, "market": "total",
            "side": side, "line": line, "take_bet": f"{side}_total",
            "dk_odds_american": odds, "dk_odds_decimal": dec,
            "model_prob": model_prob, "ev": ev, "kelly": kelly,
        })
    return select_candidate(candidates,
                            CONFIG["total"].get("pick_preference", "best_ev"),
                            "total", row.get("game_id"))


# =========================
# MAIN
# =========================

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== MLB select_bets RUN {_now()} ===\n")

    summary = {
        "slates_found": 0, "slates_written": 0, "total_bets": 0,
        "moneyline_bets": 0, "run_line_bets": 0, "total_mkt_bets": 0,
        "skipped_slates": 0, "errors": 0, "counters": {},
    }
    per_slate = []

    for old in OUTPUT_DIR.glob("*.csv"):
        old.unlink()

    _log(f"INPUT_DIR : {INPUT_DIR}")
    _log(f"OUTPUT_DIR: {OUTPUT_DIR}")

    try:
        files = sorted(INPUT_DIR.glob("*_mlb_*.csv"))
        _log(f"Files found: {len(files)}")

        if not files:
            _log("No input files found", "WARN")
            _write_summary(summary, per_slate)
            return

        slates: dict = {}
        for fp in files:
            key = fp.name.split("_mlb_")[0]
            slates.setdefault(key, []).append(fp)

        summary["slates_found"] = len(slates)

        global_counters = {
            "moneyline": {"home": init_counter(), "away": init_counter()},
            "run_line":  {"home": init_counter(), "away": init_counter()},
            "total":     {"over": init_counter(), "under": init_counter()},
        }

        for slate, _ in slates.items():
            ps = {"slate": slate, "bets": 0, "ml": 0, "rl": 0, "tot": 0, "status": "ok"}
            _log(f"--- SLATE: {slate}")

            try:
                ml_path = INPUT_DIR / f"{slate}_mlb_moneyline.csv"
                rl_path = INPUT_DIR / f"{slate}_mlb_run_line.csv"
                tt_path = INPUT_DIR / f"{slate}_mlb_total.csv"

                ml_df = pd.read_csv(ml_path) if ml_path.exists() else None
                rl_df = pd.read_csv(rl_path) if rl_path.exists() else None
                tt_df = pd.read_csv(tt_path) if tt_path.exists() else None

                if rl_df is None or rl_df.empty:
                    _log(f"{slate} no run_line file — skipping", "WARN")
                    ps["status"] = "skipped"
                    summary["skipped_slates"] += 1
                    per_slate.append(ps)
                    continue

                final   = []
                seen: set = set()

                for _, row in rl_df.iterrows():
                    game_id   = row["game_id"]
                    game_date = row["game_date"]
                    away      = row["away_team"]
                    home      = row["home_team"]
                    base      = {"game_id": game_id, "game_date": game_date,
                                 "league": LEAGUE_CODE, "away_team": away, "home_team": home}

                    # Run line
                    for r in process_run_line(row, global_counters):
                        k = f"{game_id}_{r['market_type']}_{r['bet_side']}"
                        if k not in seen:
                            final.append({**base, **r})
                            seen.add(k)
                            ps["rl"] += 1

                    # Total — filter by game_date, away_team, and home_team
                    if tt_df is not None and not tt_df.empty:
                        mask = (
                            (tt_df["away_team"] == away) &
                            (tt_df["home_team"] == home) &
                            (tt_df["game_date"] == game_date)
                        )
                        for _, t in tt_df[mask].iterrows():
                            for r in process_total(t, global_counters):
                                k = f"{game_id}_{r['market_type']}_{r['bet_side']}"
                                if k not in seen:
                                    final.append({**base, **r})
                                    seen.add(k)
                                    ps["tot"] += 1

                    # Moneyline — filter by game_date, away_team, and home_team
                    if ml_df is not None and not ml_df.empty:
                        mask = (
                            (ml_df["away_team"] == away) &
                            (ml_df["home_team"] == home) &
                            (ml_df["game_date"] == game_date)
                        )
                        for _, m in ml_df[mask].iterrows():
                            for r in process_moneyline(m, global_counters):
                                k = f"{game_id}_{r['market_type']}_{r['bet_side']}"
                                if k not in seen:
                                    final.append({**base, **r})
                                    seen.add(k)
                                    ps["ml"] += 1

                ps["bets"] = len(final)

                if final:
                    out = OUTPUT_DIR / f"{slate}_MLB.csv"
                    pd.DataFrame(final).to_csv(out, index=False)
                    summary["slates_written"] += 1
                    summary["total_bets"]     += len(final)
                    summary["moneyline_bets"] += ps["ml"]
                    summary["run_line_bets"]  += ps["rl"]
                    summary["total_mkt_bets"] += ps["tot"]
                    _log(f"WROTE: {out.name} ({len(final)} bets | ml={ps['ml']} rl={ps['rl']} tot={ps['tot']})")
                else:
                    _log(f"{slate} no bets passed filters", "WARN")
                    ps["status"] = "no_bets"

            except Exception as e:
                _log(f"{slate} FAILED: {e}\n{traceback.format_exc()}", "ERROR")
                ps["status"] = "error"
                summary["errors"] += 1

            per_slate.append(ps)

        summary["counters"] = global_counters

    except Exception as e:
        _log(f"FATAL: {e}\n{traceback.format_exc()}", "ERROR")
        summary["errors"] += 1

    _write_summary(summary, per_slate)
    print("baseball select_bets complete.")


if __name__ == "__main__":
    main()
