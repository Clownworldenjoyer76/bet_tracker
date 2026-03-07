#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/select_bets_optimizer.py

from pathlib import Path

import pandas as pd

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_FILE = Path("docs/win/basketball/04_select/selected_bets.csv")
STATS_FILE = Path("docs/win/basketball/model_testing/optimizer_stats.csv")
CONFIG_PATH = Path("docs/win/basketball/model_testing/rule_config.py")


def load_config():
    cfg = {
        "EDGE_MIN": 0.05,
        "EDGE_MAX": 0.30,
        "SPREAD_MAX": 15,
        "NBA_TOTAL_MIN_DIFF": 2.0,
        "NBA_TOTAL_LINE_MAX": 245,
        "NCAAB_TOTAL_MIN": 140,
        "NCAAB_ML_LOW": -180,
        "NCAAB_ML_HIGH": -150,
        "NCAAB_ML_MIN_PROB": 0.60,
    }

    if CONFIG_PATH.exists():
        scope = {}
        exec(CONFIG_PATH.read_text(), {}, scope)
        for key in cfg:
            if key in scope:
                cfg[key] = scope[key]

    return cfg


CFG = load_config()


def f(value):
    try:
        if pd.isna(value) or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def odds_band(odds):
    bins = [-1000, -400, -300, -200, -150, -110, 0, 100, 200, 400, 1000]
    labels = [
        "[-1000,-400]",
        "(-400,-300]",
        "(-300,-200]",
        "(-200,-150]",
        "(-150,-110]",
        "(-110,0]",
        "(0,100]",
        "(100,200]",
        "(200,400]",
        "(400,1000]",
    ]

    for i in range(len(bins) - 1):
        low = bins[i]
        high = bins[i + 1]
        if i == 0 and low <= odds <= high:
            return labels[i]
        if low < odds <= high:
            return labels[i]

    return "OUTSIDE"


def line_band(market_type, line):
    if market_type == "moneyline":
        return odds_band(line)

    if market_type == "spread":
        bins = [-30, -15, -10, -7, -5, -3, -1, 0, 1, 3, 5, 7, 10, 15, 30]
    else:
        bins = [120, 130, 135, 140, 145, 150, 155, 160, 165, 170, 200]

    for i in range(len(bins) - 1):
        low = bins[i]
        high = bins[i + 1]
        if i == 0 and low <= line <= high:
            return f"[{low},{high}]"
        if low < line <= high:
            return f"({low},{high}]"

    return "OUTSIDE"


def keep_total_candidate(league, side, line, proj, edge, odds):
    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
        return False

    if odds <= -300:
        return False

    diff = abs(proj - line)

    if league == "NCAAB":
        if side == "under" and line < CFG["NCAAB_TOTAL_MIN"]:
            return False
    else:
        if diff < CFG["NBA_TOTAL_MIN_DIFF"]:
            return False
        if line > CFG["NBA_TOTAL_LINE_MAX"]:
            return False

    return True


def keep_spread_candidate(edge, spread, odds):
    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
        return False

    if odds <= -300:
        return False

    if abs(spread) > CFG["SPREAD_MAX"]:
        return False

    return True


def keep_moneyline_candidate(league, side, edge, prob, odds):
    if edge < CFG["EDGE_MIN"] or edge > CFG["EDGE_MAX"]:
        return False

    if odds <= -300:
        return False

    if league == "NCAAB":
        if side == "home" and CFG["NCAAB_ML_LOW"] <= odds <= CFG["NCAAB_ML_HIGH"]:
            return False
        if prob < CFG["NCAAB_ML_MIN_PROB"]:
            return False

    return True


def candidate_row(base_row, league, market_type, bet_side, line, take_odds, candidate_edge):
    row = base_row.copy()
    row["league"] = league
    row["market_type"] = market_type
    row["bet_side"] = bet_side
    row["line"] = line
    row["take_odds"] = take_odds
    row["candidate_edge"] = candidate_edge
    row["odds_band"] = odds_band(take_odds)
    row["line_band"] = line_band(market_type, line)
    return row


def main():
    total_rows = 0
    candidates_after_edge = 0
    candidates_after_odds = 0
    candidates_after_rules = 0

    all_candidates = []

    for csv_file in sorted(INPUT_DIR.glob("*.csv")):
        df = pd.read_csv(csv_file)
        if df.empty:
            continue

        fname = csv_file.name.lower()
        league = "NBA" if "_nba_" in fname else "NCAAB"

        for _, row in df.iterrows():
            total_rows += 1

            if "total" in fname:
                line = f(row.get("total"))
                proj = f(row.get("total_projected_points"))

                for side in ["over", "under"]:
                    edge = f(row.get(f"{side}_edge_decimal"))
                    odds = f(row.get(f"total_{side}_juice_odds"))

                    if edge >= CFG["EDGE_MIN"]:
                        candidates_after_edge += 1
                    if edge >= CFG["EDGE_MIN"] and odds > -300:
                        candidates_after_odds += 1

                    if not keep_total_candidate(league, side, line, proj, edge, odds):
                        continue

                    candidates_after_rules += 1
                    all_candidates.append(
                        candidate_row(row, league, "total", side, line, odds, edge)
                    )

            elif "spread" in fname:
                for side in ["home", "away"]:
                    edge = f(row.get(f"{side}_edge_decimal"))
                    spread = f(row.get(f"{side}_spread"))
                    odds = f(row.get(f"{side}_spread_juice_odds"))

                    if edge >= CFG["EDGE_MIN"]:
                        candidates_after_edge += 1
                    if edge >= CFG["EDGE_MIN"] and odds > -300:
                        candidates_after_odds += 1

                    if not keep_spread_candidate(edge, spread, odds):
                        continue

                    candidates_after_rules += 1
                    all_candidates.append(
                        candidate_row(row, league, "spread", side, spread, odds, edge)
                    )

            elif "moneyline" in fname:
                for side in ["home", "away"]:
                    edge = f(row.get(f"{side}_edge_decimal"))
                    prob = f(row.get(f"{side}_prob"))
                    odds = f(row.get(f"{side}_juice_odds"))

                    if edge >= CFG["EDGE_MIN"]:
                        candidates_after_edge += 1
                    if edge >= CFG["EDGE_MIN"] and odds > -300:
                        candidates_after_odds += 1

                    if not keep_moneyline_candidate(league, side, edge, prob, odds):
                        continue

                    candidates_after_rules += 1
                    all_candidates.append(
                        candidate_row(row, league, "moneyline", side, odds, odds, edge)
                    )

    out_df = pd.DataFrame(all_candidates)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if out_df.empty:
        pd.DataFrame().to_csv(OUTPUT_FILE, index=False)
        pd.DataFrame([{
            "EDGE_MIN": CFG["EDGE_MIN"],
            "EDGE_MAX": CFG["EDGE_MAX"],
            "SPREAD_MAX": CFG["SPREAD_MAX"],
            "NBA_TOTAL_MIN_DIFF": CFG["NBA_TOTAL_MIN_DIFF"],
            "NBA_TOTAL_LINE_MAX": CFG["NBA_TOTAL_LINE_MAX"],
            "NCAAB_TOTAL_MIN": CFG["NCAAB_TOTAL_MIN"],
            "NCAAB_ML_LOW": CFG["NCAAB_ML_LOW"],
            "NCAAB_ML_HIGH": CFG["NCAAB_ML_HIGH"],
            "NCAAB_ML_MIN_PROB": CFG["NCAAB_ML_MIN_PROB"],
            "TOTAL_ROWS": total_rows,
            "CANDIDATES_AFTER_EDGE": candidates_after_edge,
            "CANDIDATES_AFTER_ODDS": candidates_after_odds,
            "CANDIDATES_AFTER_RULES": candidates_after_rules,
            "FINAL_BETS": 0,
        }]).to_csv(STATS_FILE, index=False)
        return

    out_df = out_df.sort_values(
        ["league", "game_date", "away_team", "home_team", "market_type", "candidate_edge"],
        ascending=[True, True, True, True, True, False],
    )
    out_df.to_csv(OUTPUT_FILE, index=False)

    stats_row = {
        "EDGE_MIN": CFG["EDGE_MIN"],
        "EDGE_MAX": CFG["EDGE_MAX"],
        "SPREAD_MAX": CFG["SPREAD_MAX"],
        "NBA_TOTAL_MIN_DIFF": CFG["NBA_TOTAL_MIN_DIFF"],
        "NBA_TOTAL_LINE_MAX": CFG["NBA_TOTAL_LINE_MAX"],
        "NCAAB_TOTAL_MIN": CFG["NCAAB_TOTAL_MIN"],
        "NCAAB_ML_LOW": CFG["NCAAB_ML_LOW"],
        "NCAAB_ML_HIGH": CFG["NCAAB_ML_HIGH"],
        "NCAAB_ML_MIN_PROB": CFG["NCAAB_ML_MIN_PROB"],
        "TOTAL_ROWS": total_rows,
        "CANDIDATES_AFTER_EDGE": candidates_after_edge,
        "CANDIDATES_AFTER_ODDS": candidates_after_odds,
        "CANDIDATES_AFTER_RULES": candidates_after_rules,
        "FINAL_BETS": len(out_df),
        "FINAL_BETS_NBA": int((out_df["league"] == "NBA").sum()),
        "FINAL_BETS_NCAAB": int((out_df["league"] == "NCAAB").sum()),
        "FINAL_BETS_MONEYLINE": int((out_df["market_type"] == "moneyline").sum()),
        "FINAL_BETS_SPREAD": int((out_df["market_type"] == "spread").sum()),
        "FINAL_BETS_TOTAL": int((out_df["market_type"] == "total").sum()),
        "AVG_EDGE": float(out_df["candidate_edge"].mean()),
        "MEDIAN_EDGE": float(out_df["candidate_edge"].median()),
        "AVG_ODDS": float(out_df["take_odds"].mean()),
        "MEDIAN_ODDS": float(out_df["take_odds"].median()),
        "AVG_LINE": float(out_df["line"].mean()),
        "MEDIAN_LINE": float(out_df["line"].median()),
    }

    pd.DataFrame([stats_row]).to_csv(STATS_FILE, index=False)


if __name__ == "__main__":
    main()
