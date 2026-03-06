#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/select_bets_optimizer.py

import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_FILE = Path("docs/win/basketball/04_select/selected_bets.csv")
STATS_FILE = Path("docs/win/basketball/model_testing/optimizer_stats.csv")

CONFIG_PATH = Path("docs/win/basketball/model_testing/rule_config.py")


def load_config():
    cfg = {
        "EDGE_MAX": 0.30,
        "SPREAD_MAX": 20,
        "TOTAL_MIN": 140,

        "NBA_TOTAL_EDGE_MIN": 0.00,
        "NCAAB_TOTAL_EDGE_MIN": 0.00,
        "NBA_SPREAD_EDGE_MIN": 0.00,
        "NCAAB_SPREAD_EDGE_MIN": 0.00,

        "NBA_ML_HOME_EDGE_MIN": 0.00,
        "NBA_ML_AWAY_EDGE_MIN": 0.00,
        "NCAAB_ML_HOME_EDGE_MIN": 0.00,
        "NCAAB_ML_AWAY_EDGE_MIN": 0.00,

        "NBA_ML_HOME_ODDS_MIN": -10000,
        "NBA_ML_HOME_ODDS_MAX": 10000,
        "NBA_ML_AWAY_ODDS_MIN": -10000,
        "NBA_ML_AWAY_ODDS_MAX": 10000,
        "NCAAB_ML_HOME_ODDS_MIN": -10000,
        "NCAAB_ML_HOME_ODDS_MAX": 10000,
        "NCAAB_ML_AWAY_ODDS_MIN": -10000,
        "NCAAB_ML_AWAY_ODDS_MAX": 10000,
    }

    if CONFIG_PATH.exists():
        scope = {}
        exec(CONFIG_PATH.read_text(), {}, scope)
        for k in cfg:
            if k in scope:
                cfg[k] = scope[k]

    return cfg


CFG = load_config()


def f(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def avg(vals):
    return sum(vals) / len(vals) if vals else 0.0


def med(vals):
    return float(pd.Series(vals).median()) if vals else 0.0


def main():

    total_rows = 0
    candidates_after_edge = 0
    candidates_after_odds = 0
    candidates_after_rules = 0

    spread_edges = []
    total_edges = []
    ml_home_edges = {"NBA": [], "NCAAB": []}
    ml_away_edges = {"NBA": [], "NCAAB": []}
    ml_home_odds = {"NBA": [], "NCAAB": []}
    ml_away_odds = {"NBA": [], "NCAAB": []}

    all_candidates = []

    for csv_file in INPUT_DIR.glob("*.csv"):

        df = pd.read_csv(csv_file)
        fname = csv_file.name.lower()
        league = "NBA" if "nba" in fname else "NCAAB"

        for _, row in df.iterrows():

            total_rows += 1

            game_key = (
                row.get("game_date"),
                row.get("away_team"),
                row.get("home_team")
            )

            if "total" in fname:

                line = f(row.get("total"))
                proj = f(row.get("total_projected_points"))
                diff = abs(proj - line)

                edges = {
                    "over": f(row.get("over_edge_decimal")),
                    "under": f(row.get("under_edge_decimal"))
                }

                edge_min = CFG["NBA_TOTAL_EDGE_MIN"] if league == "NBA" else CFG["NCAAB_TOTAL_EDGE_MIN"]

                for side, edge in edges.items():

                    if edge < edge_min or edge > CFG["EDGE_MAX"]:
                        continue

                    candidates_after_edge += 1

                    odds = f(row.get(f"total_{side}_juice_odds"))

                    if odds <= -300:
                        continue

                    candidates_after_odds += 1

                    if league == "NCAAB":
                        if side == "under" and line < CFG["TOTAL_MIN"]:
                            continue

                    if league == "NBA":
                        if diff < 3:
                            continue
                        if line > 245:
                            continue

                    candidates_after_rules += 1
                    total_edges.append(edge)

                    new_row = row.copy()
                    new_row["market_type"] = "total"
                    new_row["bet_side"] = side
                    new_row["line"] = line
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key
                    all_candidates.append(new_row)

            elif "spread" in fname:

                edge_min = CFG["NBA_SPREAD_EDGE_MIN"] if league == "NBA" else CFG["NCAAB_SPREAD_EDGE_MIN"]

                for side in ["home", "away"]:

                    edge = f(row.get(f"{side}_edge_decimal"))
                    spread = f(row.get(f"{side}_spread"))
                    odds = f(row.get(f"{side}_spread_juice_odds"))

                    if edge < edge_min or edge > CFG["EDGE_MAX"]:
                        continue

                    candidates_after_edge += 1

                    if odds <= -300:
                        continue

                    candidates_after_odds += 1

                    if abs(spread) > CFG["SPREAD_MAX"]:
                        continue

                    candidates_after_rules += 1
                    spread_edges.append(edge)

                    new_row = row.copy()
                    new_row["market_type"] = "spread"
                    new_row["bet_side"] = side
                    new_row["line"] = spread
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key
                    all_candidates.append(new_row)

            elif "moneyline" in fname:

                for side in ["home", "away"]:

                    edge = f(row.get(f"{side}_edge_decimal"))
                    prob = f(row.get(f"{side}_prob"))
                    odds = f(row.get(f"{side}_juice_odds"))

                    if side == "home":
                        edge_min = CFG[f"{league}_ML_HOME_EDGE_MIN"]
                        odds_min = CFG[f"{league}_ML_HOME_ODDS_MIN"]
                        odds_max = CFG[f"{league}_ML_HOME_ODDS_MAX"]
                    else:
                        edge_min = CFG[f"{league}_ML_AWAY_EDGE_MIN"]
                        odds_min = CFG[f"{league}_ML_AWAY_ODDS_MIN"]
                        odds_max = CFG[f"{league}_ML_AWAY_ODDS_MAX"]

                    if edge < edge_min or edge > CFG["EDGE_MAX"]:
                        continue

                    candidates_after_edge += 1

                    if odds <= -300:
                        continue

                    candidates_after_odds += 1

                    if not (odds_min <= odds <= odds_max):
                        continue

                    if league == "NCAAB" and prob < 0.60:
                        continue

                    candidates_after_rules += 1

                    if side == "home":
                        ml_home_edges[league].append(edge)
                        ml_home_odds[league].append(odds)
                    else:
                        ml_away_edges[league].append(edge)
                        ml_away_odds[league].append(odds)

                    new_row = row.copy()
                    new_row["market_type"] = "moneyline"
                    new_row["bet_side"] = side
                    new_row["line"] = odds
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key
                    all_candidates.append(new_row)

    df = pd.DataFrame(all_candidates)

    if df.empty:
        pd.DataFrame().to_csv(OUTPUT_FILE, index=False)
        pd.DataFrame([{
            "TOTAL_ROWS": total_rows,
            "CANDIDATES_AFTER_EDGE": 0,
            "CANDIDATES_AFTER_ODDS": 0,
            "CANDIDATES_AFTER_RULES": 0,
            "FINAL_BETS_TOTAL": 0,
            "FINAL_BETS_SPREAD": 0,
            "FINAL_BETS_TOTAL_MARKET": 0,
            "FINAL_BETS_MONEYLINE": 0
        }]).to_csv(STATS_FILE, index=False)
        return

    final_rows = []

    for _, g in df.groupby("game_key"):

        totals = g[g.market_type == "total"]
        sides = g[g.market_type.isin(["spread", "moneyline"])]

        if not totals.empty:
            final_rows.append(
                totals.sort_values("candidate_edge", ascending=False).iloc[0]
            )

        if not sides.empty:
            final_rows.append(
                sides.sort_values("candidate_edge", ascending=False).iloc[0]
            )

    res_df = pd.DataFrame(final_rows).drop_duplicates()

    res_df.drop(columns=["candidate_edge", "game_key"], errors="ignore").to_csv(OUTPUT_FILE, index=False)

    stats = {
        "TOTAL_ROWS": total_rows,
        "CANDIDATES_AFTER_EDGE": candidates_after_edge,
        "CANDIDATES_AFTER_ODDS": candidates_after_odds,
        "CANDIDATES_AFTER_RULES": candidates_after_rules,
        "FINAL_BETS_TOTAL": len(res_df),
        "FINAL_BETS_SPREAD": len(res_df[res_df["market_type"] == "spread"]),
        "FINAL_BETS_TOTAL_MARKET": len(res_df[res_df["market_type"] == "total"]),
        "FINAL_BETS_MONEYLINE": len(res_df[res_df["market_type"] == "moneyline"]),
        "AVG_EDGE_SPREAD": avg(spread_edges),
        "MEDIAN_EDGE_SPREAD": med(spread_edges),
        "AVG_EDGE_TOTAL": avg(total_edges),
        "MEDIAN_EDGE_TOTAL": med(total_edges),

        "NBA_ML_HOME_EDGE_AVG": avg(ml_home_edges["NBA"]),
        "NBA_ML_HOME_EDGE_MEDIAN": med(ml_home_edges["NBA"]),
        "NBA_ML_AWAY_EDGE_AVG": avg(ml_away_edges["NBA"]),
        "NBA_ML_AWAY_EDGE_MEDIAN": med(ml_away_edges["NBA"]),
        "NCAAB_ML_HOME_EDGE_AVG": avg(ml_home_edges["NCAAB"]),
        "NCAAB_ML_HOME_EDGE_MEDIAN": med(ml_home_edges["NCAAB"]),
        "NCAAB_ML_AWAY_EDGE_AVG": avg(ml_away_edges["NCAAB"]),
        "NCAAB_ML_AWAY_EDGE_MEDIAN": med(ml_away_edges["NCAAB"]),

        "NBA_ML_HOME_ODDS_AVG": avg(ml_home_odds["NBA"]),
        "NBA_ML_HOME_ODDS_MIN": min(ml_home_odds["NBA"]) if ml_home_odds["NBA"] else 0.0,
        "NBA_ML_HOME_ODDS_MAX": max(ml_home_odds["NBA"]) if ml_home_odds["NBA"] else 0.0,
        "NBA_ML_AWAY_ODDS_AVG": avg(ml_away_odds["NBA"]),
        "NBA_ML_AWAY_ODDS_MIN": min(ml_away_odds["NBA"]) if ml_away_odds["NBA"] else 0.0,
        "NBA_ML_AWAY_ODDS_MAX": max(ml_away_odds["NBA"]) if ml_away_odds["NBA"] else 0.0,

        "NCAAB_ML_HOME_ODDS_AVG": avg(ml_home_odds["NCAAB"]),
        "NCAAB_ML_HOME_ODDS_MIN": min(ml_home_odds["NCAAB"]) if ml_home_odds["NCAAB"] else 0.0,
        "NCAAB_ML_HOME_ODDS_MAX": max(ml_home_odds["NCAAB"]) if ml_home_odds["NCAAB"] else 0.0,
        "NCAAB_ML_AWAY_ODDS_AVG": avg(ml_away_odds["NCAAB"]),
        "NCAAB_ML_AWAY_ODDS_MIN": min(ml_away_odds["NCAAB"]) if ml_away_odds["NCAAB"] else 0.0,
        "NCAAB_ML_AWAY_ODDS_MAX": max(ml_away_odds["NCAAB"]) if ml_away_odds["NCAAB"] else 0.0,
    }

    pd.DataFrame([stats]).to_csv(STATS_FILE, index=False)


if __name__ == "__main__":
    main()
