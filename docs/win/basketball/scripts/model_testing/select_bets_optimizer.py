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
    except:
        return 0.0


def main():

    total_rows = 0
    edge_pass = 0
    odds_pass = 0
    spread_pass = 0
    final_candidates = []

    for csv_file in INPUT_DIR.glob("*.csv"):

        df = pd.read_csv(csv_file)
        fname = csv_file.name.lower()
        league = "NBA" if "nba" in fname else "NCAAB"

        records = df.to_dict("records")

        for row in records:

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

                for side, edge in edges.items():

                    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
                        continue

                    edge_pass += 1

                    odds = f(row.get(f"total_{side}_juice_odds"))

                    if odds <= -300:
                        continue

                    odds_pass += 1

                    if league == "NCAAB":
                        if side == "under" and line < CFG["TOTAL_MIN"]:
                            continue

                    if league == "NBA":
                        if diff < 3:
                            continue
                        if line > 245:
                            continue

                    spread_pass += 1

                    new_row = row.copy()

                    new_row["market_type"] = "total"
                    new_row["bet_side"] = side
                    new_row["line"] = line
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key

                    final_candidates.append(new_row)

            elif "spread" in fname:

                for side in ["home", "away"]:

                    edge = f(row.get(f"{side}_edge_decimal"))
                    spread = f(row.get(f"{side}_spread"))
                    odds = f(row.get(f"{side}_spread_juice_odds"))

                    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
                        continue

                    edge_pass += 1

                    if odds <= -300:
                        continue

                    odds_pass += 1

                    if abs(spread) > CFG["SPREAD_MAX"]:
                        continue

                    spread_pass += 1

                    new_row = row.copy()

                    new_row["market_type"] = "spread"
                    new_row["bet_side"] = side
                    new_row["line"] = spread
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key

                    final_candidates.append(new_row)

            elif "moneyline" in fname:

                for side in ["home", "away"]:

                    edge = f(row.get(f"{side}_edge_decimal"))
                    prob = f(row.get(f"{side}_prob"))
                    odds = f(row.get(f"{side}_juice_odds"))

                    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
                        continue

                    edge_pass += 1

                    if odds <= -300:
                        continue

                    odds_pass += 1

                    if league == "NCAAB":

                        low = CFG["ML_LOW"]
                        high = CFG["ML_HIGH"]

                        if side == "home" and low <= odds <= high:
                            continue

                        if prob < 0.60:
                            continue

                    spread_pass += 1

                    new_row = row.copy()

                    new_row["market_type"] = "moneyline"
                    new_row["bet_side"] = side
                    new_row["line"] = odds
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key

                    final_candidates.append(new_row)

    df = pd.DataFrame(final_candidates)

    if df.empty:
        pd.DataFrame().to_csv(OUTPUT_FILE, index=False)
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

    res_df.drop(
        columns=["candidate_edge", "game_key"],
        errors="ignore"
    ).to_csv(OUTPUT_FILE, index=False)

    stats = pd.DataFrame([{
        "TOTAL_ROWS": total_rows,
        "EDGE_FILTER_PASS": edge_pass,
        "ODDS_FILTER_PASS": odds_pass,
        "SPREAD_FILTER_PASS": spread_pass,
        "FINAL_BETS": len(res_df)
    }])

    if STATS_FILE.exists():
        prev = pd.read_csv(STATS_FILE)
        stats = pd.concat([prev, stats], ignore_index=True)

    stats.to_csv(STATS_FILE, index=False)


if __name__ == "__main__":
    main()
