#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/band_performance_report.py

from pathlib import Path

import pandas as pd

NBA_FILE = Path("docs/win/basketball/model_testing/graded/nba/NBA_final.csv")
NCAAB_FILE = Path("docs/win/basketball/model_testing/graded/ncaab/NCAAB_final.csv")
OUTPUT = Path("docs/win/basketball/model_testing/band_performance_report.csv")

ML_BINS = [-1000, -400, -300, -200, -150, -110, 0, 100, 200, 400, 1000]
SPREAD_BINS = [-30, -15, -10, -7, -5, -3, -1, 0, 1, 3, 5, 7, 10, 15, 30]
TOTAL_BINS = [120, 130, 135, 140, 145, 150, 155, 160, 165, 170, 200]


def bucket(series, bins):
    return pd.cut(series, bins=bins, include_lowest=True)


def profit_from_row(row):
    result = row.get("bet_result", "")
    odds = row.get("take_odds", -110)

    if pd.isna(odds) or odds == "":
        odds = -110

    odds = float(odds)

    if result == "Win":
        if odds > 0:
            return odds / 100.0
        return 100.0 / abs(odds)

    if result == "Loss":
        return -1.0

    return 0.0


def build_table(df, league):
    rows = []

    sections = [
        ("moneyline", ["home", "away"], ML_BINS),
        ("spread", ["home", "away"], SPREAD_BINS),
        ("total", ["over", "under"], TOTAL_BINS),
    ]

    for market_type, sides, bins in sections:
        market_df = df[df.market_type == market_type].copy()

        for side in sides:
            sub = market_df[market_df.bet_side == side].copy()
            if sub.empty:
                continue

            sub["line"] = pd.to_numeric(sub["line"], errors="coerce")
            sub = sub.dropna(subset=["line"])
            if sub.empty:
                continue

            sub["band"] = bucket(sub["line"], bins)
            sub["profit"] = sub.apply(profit_from_row, axis=1)

            grouped = sub.groupby("band", dropna=False)

            for band, grp in grouped:
                bets = len(grp)
                wins = int((grp.bet_result == "Win").sum())
                losses = int((grp.bet_result == "Loss").sum())
                pushes = int((grp.bet_result == "Push").sum())
                profit = float(grp["profit"].sum())
                risk = float(bets) if bets else 0.0
                roi = (profit / risk) if risk else 0.0

                rows.append({
                    "league": league,
                    "market_type": market_type,
                    "side": side,
                    "band": str(band),
                    "bets": bets,
                    "wins": wins,
                    "losses": losses,
                    "pushes": pushes,
                    "win_pct": (wins / bets) if bets else 0.0,
                    "profit": profit,
                    "roi": roi,
                    "avg_odds": float(pd.to_numeric(grp.get("take_odds"), errors="coerce").mean()) if "take_odds" in grp.columns else 0.0,
                    "avg_edge": float(pd.to_numeric(grp.get("candidate_edge"), errors="coerce").mean()) if "candidate_edge" in grp.columns else 0.0,
                })

    return rows


def main():
    rows = []

    if NBA_FILE.exists():
        nba = pd.read_csv(NBA_FILE)
        rows += build_table(nba, "NBA")

    if NCAAB_FILE.exists():
        ncaab = pd.read_csv(NCAAB_FILE)
        rows += build_table(ncaab, "NCAAB")

    df = pd.DataFrame(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if not df.empty:
        df = df.sort_values(["league", "market_type", "side", "band"])

    df.to_csv(OUTPUT, index=False)


if __name__ == "__main__":
    main()
