#!/usr/bin/env python3
# docs/win/soccer/scripts/04_select/soccer_select_bets.py

import traceback
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd
import yaml

BASE = Path(__file__).resolve().parents[2]

INPUT_DIR   = BASE / "03_edges"
OUTPUT_DIR  = BASE / "04_select"
CONFIG_PATH = BASE / "config" / "markets.yaml"

ERROR_DIR = BASE / "errors" / "04_select"
LOG_FILE  = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# LOGGING
# =========================

def _now():
    return datetime.now(UTC).isoformat()


def _log(msg: str, level: str = "INFO"):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{_now()} | {level:<5} | {msg.rstrip()}\n")


def _write_summary(summary: dict, per_market: dict, per_date: dict) -> None:
    lines = [
        "",
        "=" * 60,
        f"SUMMARY  {_now()}",
        "=" * 60,
        f"  files_processed : {summary['files_processed']}",
        f"  total_bets      : {summary['total_bets']}",
        f"  dates_written   : {summary['dates_written']}",
        f"  skipped_files   : {summary['skipped']}",
        f"  errors          : {summary['errors']}",
        "",
        "--- By Market ---",
        f"  {'market':<15} {'bets':>6}",
    ]
    for market, count in sorted(per_market.items()):
        lines.append(f"  {market:<15} {count:>6}")
    lines += ["", "--- By Date ---",
              f"  {'date':<14} {'bets':>6} {'file'}"]
    for date, info in sorted(per_date.items()):
        lines.append(f"  {date:<14} {info['bets']:>6}  {info['file']}")
    status = "SUCCESS" if summary["errors"] == 0 else "COMPLETED WITH ERRORS"
    lines += ["", f"STATUS: {status}", "=" * 60]
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# =========================
# LOAD CONFIG
# =========================

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)["markets"]["soccer"]


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


def check_rules(ev, kelly, odds, rules):
    if ev is None or kelly is None:
        return False
    if ev < rules["ev_min"] or ev > rules["ev_max"]:
        return False
    if kelly < rules["kelly_min"] or kelly > rules["kelly_max"]:
        return False
    if "odds_bands" in rules and not in_range(odds, rules["odds_bands"]):
        return False
    return True


def base_row(row):
    return {
        "game_id":    row.get("game_id"),
        "sport":      row.get("sport"),
        "league":     row.get("league"),
        "match_date": row.get("match_date"),
        "match_time": row.get("match_time"),
        "home_team":  row.get("home_team"),
        "away_team":  row.get("away_team"),
    }


# =========================
# MARKET PROCESSORS
# =========================

def process_match(df):
    results = []
    for _, row in df.iterrows():
        for side in ["home", "draw", "away"]:
            rules = CONFIG["match_odds"].get(side)
            if not rules or not rules.get("enabled"):
                continue
            ev    = fv(row.get(f"{side}_ev"))
            kelly = fv(row.get(f"{side}_kelly"))
            odds  = fv(row.get(f"dk_{side}_decimal"))
            if not check_rules(ev, kelly, odds, rules):
                continue
            results.append({
                **base_row(row),
                "market": "match_odds",
                "side": side,
                "odds": odds,
                "ev": ev,
                "kelly": kelly
            })
    return results


def process_totals(df, file_name):
    results = []

    if "total_25" in file_name:
        market = "total25"
        over_odds_col = "dk_over25_decimal"
        under_odds_col = "dk_under25_decimal"
    elif "total_35" in file_name:
        market = "total35"
        over_odds_col = "dk_over35_decimal"
        under_odds_col = "dk_under35_decimal"
    else:
        return results

    for _, row in df.iterrows():
        for side in ["over", "under"]:
            rules = CONFIG["totals"].get(side)
            if not rules or not rules.get("enabled"):
                continue

            ev = fv(row.get(f"{side}_ev"))
            kelly = fv(row.get(f"{side}_kelly"))

            if side == "over":
                odds = fv(row.get(over_odds_col))
            else:
                odds = fv(row.get(under_odds_col))

            if not check_rules(ev, kelly, odds, rules):
                continue

            results.append({
                **base_row(row),
                "market": market,
                "side": side,
                "odds": odds,
                "ev": ev,
                "kelly": kelly
            })

    return results


def process_btts(df):
    results = []
    for _, row in df.iterrows():
        for side in ["yes", "no"]:
            rules = CONFIG["btts"].get(side)
            if not rules or not rules.get("enabled"):
                continue
            ev    = fv(row.get(f"{side}_ev"))
            kelly = fv(row.get(f"{side}_kelly"))
            odds  = fv(row.get(f"btts_{side}"))
            if not check_rules(ev, kelly, odds, rules):
                continue
            results.append({
                **base_row(row),
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
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== soccer select_bets RUN {_now()} ===\n")

    summary = {
        "files_processed": 0,
        "total_bets": 0,
        "dates_written": 0,
        "skipped": 0,
        "errors": 0,
    }
    per_market: dict = {}
    per_date: dict = {}
    all_bets = []

    _log(f"INPUT_DIR : {INPUT_DIR}")
    _log(f"OUTPUT_DIR: {OUTPUT_DIR}")

    input_files = sorted(INPUT_DIR.glob("*.csv"))
    _log(f"Files found: {len(input_files)}")

    try:
        for file in input_files:
            _log(f"--- FILE: {file.name}")
            try:
                df = pd.read_csv(file)

                if df.empty:
                    _log(f"{file.name} empty — skipping")
                    summary["skipped"] += 1
                    continue

                if "match_odds" in file.name:
                    bets = process_match(df)
                elif "total" in file.name:
                    bets = process_totals(df, file.name)
                elif "btts" in file.name:
                    bets = process_btts(df)
                else:
                    _log(f"SKIP unrecognized file: {file.name}")
                    summary["skipped"] += 1
                    continue

                _log(f"{file.name} | {len(bets)} bets selected")
                summary["files_processed"] += 1
                all_bets += bets

                for b in bets:
                    mkt = b.get("market", "unknown")
                    per_market[mkt] = per_market.get(mkt, 0) + 1

            except Exception as e:
                _log(f"{file.name} FAILED: {e}\n{traceback.format_exc()}", "ERROR")
                summary["errors"] += 1

        if not all_bets:
            _log("No bets selected across all files", "WARN")
            _write_summary(summary, per_market, per_date)
            return

        df_all = pd.DataFrame(all_bets)
        summary["total_bets"] = len(df_all)

        for date, group in df_all.groupby("match_date"):
            out_path = OUTPUT_DIR / f"{date}_soccer_bets.csv"
            group.to_csv(out_path, index=False)
            summary["dates_written"] += 1
            per_date[str(date)] = {"bets": len(group), "file": out_path.name}
            _log(f"WROTE: {out_path} ({len(group)} bets)")

    except Exception as e:
        _log(f"FATAL: {e}\n{traceback.format_exc()}", "ERROR")
        summary["errors"] += 1

    _write_summary(summary, per_market, per_date)
    print("soccer select_bets complete.")


if __name__ == "__main__":
    main()
