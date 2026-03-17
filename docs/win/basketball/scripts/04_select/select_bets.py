#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
import re
import yaml

###############################################################
######################## PATH CONFIG ##########################
###############################################################

INPUT_DIR = Path("docs/win/basketball/03_edges/ev_kelly")
SELECT_DIR = Path("docs/win/basketball/04_select")
DAILY_DIR = SELECT_DIR / "daily_slate"
TOTALS_DIR = DAILY_DIR / "totals"
CONFIG_PATH = Path("docs/win/basketball/config/markets.yaml")

SELECT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

###############################################################
######################## BAND HELPER ##########################
###############################################################

def in_bands(value, bands):
    for low, high in bands:
        if low <= value <= high:
            return True
    return False

###############################################################
######################## RULE ENGINE ##########################
###############################################################

def compare_value(value, spec):
    if value is None:
        return False

    if "gt" in spec and not (value > spec["gt"]):
        return False
    if "gte" in spec and not (value >= spec["gte"]):
        return False
    if "lt" in spec and not (value < spec["lt"]):
        return False
    if "lte" in spec and not (value <= spec["lte"]):
        return False

    return True


def evaluate_rule(rule, context):
    if "all" in rule:
        return all(evaluate_rule(item, context) for item in rule["all"])

    if "any" in rule:
        return any(evaluate_rule(item, context) for item in rule["any"])

    field = rule.get("field")
    if not field:
        return False

    value = context.get(field)
    return compare_value(value, rule)


def any_rule_matches(rules, context):
    if not rules:
        return False
    return any(evaluate_rule(rule, context) for rule in rules)


def get_edge_bands_from_rules(rules, context):
    if not rules:
        return None

    for rule in rules:
        when = rule.get("when", {})
        if evaluate_rule(when, context):
            return rule.get("edge_bands")

    return None

###############################################################
######################## HELPERS ##############################
###############################################################

def f(x):
    try:
        if pd.isna(x):
            return 0
        return float(x)
    except Exception:
        return 0


def detect_market(filename):
    name = filename.lower()

    if "moneyline" in name or "_ml" in name:
        return "moneyline"

    if "spread" in name:
        return "spread"

    if "total" in name:
        return "total"

    return ""


def extract_date(filename):
    m = re.search(r"\d{4}_\d{2}_\d{2}", filename)
    if m:
        return m.group(0)
    return None


def clear_daily_outputs():
    for fpath in DAILY_DIR.glob("*_nba.csv"):
        fpath.unlink(missing_ok=True)
    for fpath in DAILY_DIR.glob("*_ncaab.csv"):
        fpath.unlink(missing_ok=True)

###############################################################
######################## CONFIG HELPERS #######################
###############################################################

def market_cfg(league, market_type):
    return CONFIG["markets"][league.lower()][market_type]


def side_cfg(league, market_type, side):
    return market_cfg(league, market_type)[side]

###############################################################
######################## MONEYLINE ############################
###############################################################

def moneyline(row, league):

    cfg = market_cfg(league, "moneyline")
    if not cfg.get("enabled", False):
        return False, "", "", 0

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    home_cfg = side_cfg(league, "moneyline", "home")
    away_cfg = side_cfg(league, "moneyline", "away")

    home_valid = (
        home_cfg.get("enabled", False)
        and in_bands(home_ml, home_cfg.get("odds_bands", []))
        and in_bands(home_edge, home_cfg.get("edge_bands", []))
    )

    away_valid = (
        away_cfg.get("enabled", False)
        and in_bands(away_ml, away_cfg.get("odds_bands", []))
        and in_bands(away_edge, away_cfg.get("edge_bands", []))
    )

    if home_valid and away_valid:
        if home_edge >= away_edge:
            return True, "home", home_ml, home_edge
        return True, "away", away_ml, away_edge

    if home_valid:
        return True, "home", home_ml, home_edge

    if away_valid:
        return True, "away", away_ml, away_edge

    return False, "", "", 0

###############################################################
######################## SPREAD ###############################
###############################################################

def spread(row, league):

    cfg = market_cfg(league, "spread")
    if not cfg.get("enabled", False):
        return False, "", "", 0

    home_line = f(row.get("home_spread"))
    away_line = f(row.get("away_spread"))

    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    context = {
        "home_line": home_line,
        "away_line": away_line,
        "home_edge": home_edge,
        "away_edge": away_edge,
    }

    if any_rule_matches(cfg.get("block_rules", []), context):
        return False, "", "", 0

    home_cfg = side_cfg(league, "spread", "home")
    away_cfg = side_cfg(league, "spread", "away")

    home_valid = (
        home_cfg.get("enabled", False)
        and in_bands(home_line, home_cfg.get("line_bands", []))
        and in_bands(home_edge, home_cfg.get("edge_bands", []))
    )

    away_edge_bands = get_edge_bands_from_rules(away_cfg.get("edge_rules", []), context)
    if away_edge_bands is None:
        away_edge_bands = away_cfg.get("edge_bands", [])

    away_valid = (
        away_cfg.get("enabled", False)
        and in_bands(away_line, away_cfg.get("line_bands", []))
        and in_bands(away_edge, away_edge_bands)
    )

    if home_valid and away_valid:
        if home_edge >= away_edge:
            return True, "home", home_line, home_edge
        return True, "away", away_line, away_edge

    if home_valid:
        return True, "home", home_line, home_edge

    if away_valid:
        return True, "away", away_line, away_edge

    return False, "", "", 0

###############################################################
######################## TOTAL ################################
###############################################################

def total(row, league):

    cfg = market_cfg(league, "total")
    if not cfg.get("enabled", False):
        return False, "", "", 0

    line = f(row.get("total"))

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    if over_edge >= under_edge:
        side = "over"
        edge = over_edge
    else:
        side = "under"
        edge = under_edge

    side_config = side_cfg(league, "total", side)

    if (
        side_config.get("enabled", False)
        and in_bands(line, side_config.get("line_bands", []))
        and in_bands(edge, side_config.get("edge_bands", []))
    ):
        return True, side, line, edge

    return False, "", "", 0

###############################################################
######################## PROCESS FILE #########################
###############################################################

def process_file(file):

    df = pd.read_csv(file)

    if df.empty:
        return None

    league = "NBA" if "nba" in file.name.lower() else "NCAAB"
    market_type = detect_market(file.name)
    game_date = extract_date(file.name)

    if market_type == "" or game_date is None:
        return None

    rows = []

    for _, row in df.iterrows():

        if market_type == "moneyline":
            ok, side, line, edge = moneyline(row, league)

        elif market_type == "spread":
            ok, side, line, edge = spread(row, league)

        else:
            ok, side, line, edge = total(row, league)

        if ok:
            r = row.to_dict()
            r["bet_side"] = side
            r["line"] = line
            r["selected_edge"] = edge
            r["market_type"] = market_type
            r["market"] = league
            r["game_date"] = game_date
            rows.append(r)

    if rows:
        out = pd.DataFrame(rows)
        out["source_date"] = game_date
        out["source_league"] = league
        return out

    return None

###############################################################
######################## MERGE OUTPUTS ########################
###############################################################

def merge_outputs():

    nba_files = sorted(DAILY_DIR.glob("*_nba.csv"))
    ncaab_files = sorted(DAILY_DIR.glob("*_ncaab.csv"))

    if nba_files:
        dfs = [pd.read_csv(f) for f in nba_files if f.stat().st_size > 0]
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            df.to_csv(DAILY_DIR / "nba_selected.csv", index=False)
            df.to_csv(TOTALS_DIR / "NBA_final.csv", index=False)

    if ncaab_files:
        dfs = [pd.read_csv(f) for f in ncaab_files if f.stat().st_size > 0]
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            df.to_csv(DAILY_DIR / "ncaab_selected.csv", index=False)
            df.to_csv(TOTALS_DIR / "NCAAB_final.csv", index=False)

###############################################################
######################## MAIN #################################
###############################################################

def main():

    clear_daily_outputs()

    dfs = []

    for file in sorted(INPUT_DIR.glob("*.csv")):
        df = process_file(file)

        if df is not None:
            dfs.append(df)

    if not dfs:
        print("No bets selected")
        return

    df = pd.concat(dfs, ignore_index=True)

    for (date_value, league_value), sub in df.groupby(["source_date", "source_league"], dropna=False):

        out_df = sub.drop(columns=["source_date", "source_league"], errors="ignore")

        if league_value == "NBA":
            out_file = DAILY_DIR / f"{date_value}_nba.csv"
        else:
            out_file = DAILY_DIR / f"{date_value}_ncaab.csv"

        out_df.to_csv(out_file, index=False)

    merge_outputs()

    nba_count = len(df[df["source_league"] == "NBA"])
    ncaab_count = len(df[df["source_league"] == "NCAAB"])

    print("NBA bets:", nba_count)
    print("NCAAB bets:", ncaab_count)


if __name__ == "__main__":
    main()
