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
        "EDGE_MIN": 0.10,
        "EDGE_MAX": 0.30,
        "SPREAD_MAX": 20,
        "TOTAL_MIN": 140,
        "ML_LOW": -180,
        "ML_HIGH": -150
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


def main():

    total_rows = 0
    candidates_after_edge = 0
    candidates_after_odds = 0
    candidates_after_rules = 0

    spread_edges = []
    total_edges = []
    ml_edges = []

    all_candidates = []

    for csv_file in INPUT_DIR.glob("*.csv"):

        df = pd.read_csv(csv_file)
        fname = csv_file.name.lower()
        league = "NBA" if "_nba_" in fname else "NCAAB"

        for _, row in df.iterrows():

            total_rows += 1

            if "total" in fname:

                line = f(row.get("total"))
                proj = f(row.get("total_projected_points"))
                diff = abs(proj - line)

                edges = {
                    "over": f(row.get("over_edge_decimal")),
                    "under": f(row.get("under_edge_decimal"))
                }

                for side, edge in edges.items():

                    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
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

                    all_candidates.append(new_row)

            elif "spread" in fname:

                for side in ["home", "away"]:

                    edge = f(row.get(f"{side}_edge_decimal"))
                    spread = f(row.get(f"{side}_spread"))
                    odds = f(row.get(f"{side}_spread_juice_odds"))

                    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
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

                    all_candidates.append(new_row)

            elif "moneyline" in fname:

                for side in ["home", "away"]:

                    edge = f(row.get(f"{side}_edge_decimal"))
                    prob = f(row.get(f"{side}_prob"))
                    odds = f(row.get(f"{side}_juice_odds"))

                    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
                        continue

                    candidates_after_edge += 1

                    if odds <= -300:
                        continue

                    candidates_after_odds += 1

                    if league == "NCAAB":
                        low = CFG["ML_LOW"]
                        high = CFG["ML_HIGH"]

                        if side == "home" and low <= odds <= high:
                            continue

                        if prob < 0.60:
                            continue

                    candidates_after_rules += 1
                    ml_edges.append(edge)

                    new_row = row.copy()
                    new_row["market_type"] = "moneyline"
                    new_row["bet_side"] = side
                    new_row["line"] = odds
                    new_row["candidate_edge"] = edge

                    all_candidates.append(new_row)

    df = pd.DataFrame(all_candidates)

    if df.empty:
        pd.DataFrame().to_csv(OUTPUT_FILE, index=False)
        return

    df.drop(columns=["candidate_edge"], errors="ignore").to_csv(OUTPUT_FILE, index=False)

    stats_df = pd.DataFrame([{
        "TOTAL_ROWS": total_rows,
        "CANDIDATES_AFTER_EDGE": candidates_after_edge,
        "CANDIDATES_AFTER_ODDS": candidates_after_odds,
        "CANDIDATES_AFTER_RULES": candidates_after_rules,
        "FINAL_BETS_TOTAL": len(df),
        "FINAL_BETS_SPREAD": len(df[df["market_type"] == "spread"]),
        "FINAL_BETS_TOTAL_MARKET": len(df[df["market_type"] == "total"]),
        "FINAL_BETS_MONEYLINE": len(df[df["market_type"] == "moneyline"]),
        "AVG_EDGE_SPREAD": sum(spread_edges) / len(spread_edges) if spread_edges else 0,
        "MEDIAN_EDGE_SPREAD": pd.Series(spread_edges).median() if spread_edges else 0,
        "AVG_EDGE_TOTAL": sum(total_edges) / len(total_edges) if total_edges else 0,
        "MEDIAN_EDGE_TOTAL": pd.Series(total_edges).median() if total_edges else 0,
        "AVG_EDGE_ML": sum(ml_edges) / len(ml_edges) if ml_edges else 0,
        "MEDIAN_EDGE_ML": pd.Series(ml_edges).median() if ml_edges else 0
    }])

    if STATS_FILE.exists():
        prev = pd.read_csv(STATS_FILE)
        stats_df = pd.concat([prev, stats_df], ignore_index=True)

    stats_df.to_csv(STATS_FILE, index=False)


if __name__ == "__main__":
    main()
