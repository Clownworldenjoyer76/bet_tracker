# docs/win/final_scores/scripts/05_results/generate_summary.py

import pandas as pd
import glob
import os
from pathlib import Path
from datetime import datetime

ERROR_LOG = Path("docs/win/final_scores/scripts/05_results/summary_audit.txt")


def extract_edge(row):

    try:

        side = row.get("bet_side")
        market = row.get("market_type")

        if market == "moneyline":

            if side == "home":
                return row.get("home_ml_edge_decimal", 0)

            if side == "away":
                return row.get("away_ml_edge_decimal", 0)

        if market == "spread":

            if side == "home":
                return row.get("home_spread_edge_decimal", 0)

            if side == "away":
                return row.get("away_spread_edge_decimal", 0)

        if market == "total":

            if side == "over":
                return row.get("over_edge_decimal", 0)

            if side == "under":
                return row.get("under_edge_decimal", 0)

    except:
        pass

    return 0


def generate_reports():

    sports = [
        {"name": "nba", "suffix": "NBA", "markets": ["moneyline", "spread", "total"]},
        {"name": "ncaab", "suffix": "NCAAB", "markets": ["moneyline", "spread", "total"]},
    ]

    for sport in sports:

        results_dir = f"docs/win/final_scores/results/{sport['name']}/graded"

        files = glob.glob(os.path.join(results_dir, f"*_results_{sport['suffix']}.csv"))

        if not files:
            continue

        df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

        df = df.drop_duplicates(subset=[
            "game_date",
            "away_team",
            "home_team",
            "market_type",
            "bet_side",
            "line"
        ])

        df["edge_used"] = df.apply(extract_edge, axis=1)

        wins = df[df["bet_result"] == "Win"]["edge_used"]
        losses = df[df["bet_result"] == "Loss"]["edge_used"]

        win_avg = wins.mean() if not wins.empty else 0
        loss_avg = losses.mean() if not losses.empty else 0

        print("\n", sport["suffix"])
        print("Average win edge:", round(win_avg, 4))
        print("Average loss edge:", round(loss_avg, 4))

        if win_avg > loss_avg:
            print("Edge signal direction: CORRECT")
        else:
            print("Edge signal direction: INVERTED")


if __name__ == "__main__":
    generate_reports()
