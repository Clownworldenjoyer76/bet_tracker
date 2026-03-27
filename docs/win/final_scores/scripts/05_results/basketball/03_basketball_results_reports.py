#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/final_scores/intermediate")

BASE_OUTPUT_DIR = Path("docs/win/final_scores/deeper_summaries")
NBA_OUTPUT_DIR = BASE_OUTPUT_DIR / "nba"
NCAAB_OUTPUT_DIR = BASE_OUTPUT_DIR / "ncaab"
NBA_DETAIL_DIR = NBA_OUTPUT_DIR / "by_market"
NCAAB_DETAIL_DIR = NCAAB_OUTPUT_DIR / "by_market"

NBA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
NCAAB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
NBA_DETAIL_DIR.mkdir(parents=True, exist_ok=True)
NCAAB_DETAIL_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------
# EDGE BUCKET (IMPROVED)
# -----------------------
def _edge_bucket(x):
    try:
        x = float(x)
    except:
        return "UNBUCKETED"
    if x < 0.05: return "0.00–0.05"
    if x < 0.075: return "0.05–0.075"
    if x < 0.10: return "0.075–0.10"
    if x < 0.15: return "0.10–0.15"
    if x < 0.20: return "0.15–0.20"
    return "0.20+"

# -----------------------
# ENRICHMENT
# -----------------------
def enrich_work(df):
    df = df.copy()

    def _take_odds(row):
        mt = str(row.get("market_type", "")).lower()
        side = str(row.get("bet_side", "")).lower()
        if mt == "moneyline":
            col = "home_dk_moneyline_american" if side == "home" else "away_dk_moneyline_american"
        elif mt == "spread":
            col = "home_dk_spread_american" if side == "home" else "away_dk_spread_american"
        elif mt == "total":
            col = "dk_total_over_american" if side == "over" else "dk_total_under_american"
        else:
            return None
        return row.get(col)

    def _kelly_value(row):
        mt = str(row.get("market_type", "")).lower()
        side = str(row.get("bet_side", "")).lower()
        if mt == "moneyline":
            col = "home_ml_kelly" if side == "home" else "away_ml_kelly"
        elif mt == "spread":
            col = "home_spread_kelly" if side == "home" else "away_spread_kelly"
        elif mt == "total":
            col = "over_kelly" if side == "over" else "under_kelly"
        else:
            return None
        return row.get(col)

    def _kelly_bucket(k):
        try:
            k = float(k)
        except:
            return "UNBUCKETED"
        if k < 0.01: return "0-1%"
        if k < 0.02: return "1-2%"
        if k < 0.05: return "2-5%"
        return "5%+"

    def _odds_bucket(value):
        try:
            value = float(value)
        except:
            return "UNBUCKETED"
        if value <= -200: return "≤-200"
        if value <= -150: return "-199 to -150"
        if value <= -110: return "-149 to -110"
        if value <= 100: return "-109 to +100"
        if value <= 150: return "+101 to +150"
        return "+150+"

    def _units_won(odds, result):
        if result == "Push": return 0
        if result == "Loss": return -1
        try:
            odds = float(odds)
        except:
            return None
        return odds / 100 if odds > 0 else 100 / abs(odds)

    df["take_odds"] = df.apply(_take_odds, axis=1)
    df["kelly_value"] = df.apply(_kelly_value, axis=1)
    df["kelly_bucket"] = df["kelly_value"].apply(_kelly_bucket)
    df["odds_bucket"] = df["take_odds"].apply(_odds_bucket)
    df["bet_units"] = df.apply(lambda r: _units_won(r["take_odds"], r["bet_result"]), axis=1)
    df["edge_bucket"] = df["selected_edge"].apply(_edge_bucket)

    return df

# -----------------------
# AGGREGATION (UPGRADED)
# -----------------------
def aggregate_full(df, group_cols):
    rows = []
    for keys, sub in df.groupby(group_cols, dropna=False):

        if not isinstance(keys, tuple):
            keys = (keys,)

        wins = (sub["bet_result"] == "Win").sum()
        losses = (sub["bet_result"] == "Loss").sum()
        bets = len(sub)

        units = sub["bet_units"].sum()
        roi = units / bets if bets else 0

        avg_edge = sub["selected_edge"].mean()
        avg_odds = sub["take_odds"].mean()

        avg_units = units / bets if bets else 0
        std_units = sub["bet_units"].std()

        row = {col: keys[i] for i, col in enumerate(group_cols)}
        row.update({
            "bets": bets,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / (wins + losses), 4) if (wins + losses) else 0,
            "units": round(units, 4),
            "roi": round(roi, 4),
            "avg_edge": round(avg_edge, 4),
            "avg_odds": round(avg_odds, 1),
            "avg_units_per_bet": round(avg_units, 4),
            "std_units": round(std_units, 4) if std_units is not None else None
        })

        rows.append(row)

    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)

# -----------------------
# DETAIL REPORTS (UPGRADED)
# -----------------------
def build_detail_reports(work, detail_dir, league):

    for market in ["moneyline", "spread", "total"]:
        df = work[work["market_type"] == market]
        if df.empty:
            continue

        prefix = f"{league}_{market}"

        # CORE
        aggregate_full(df, ["edge_bucket"]).to_csv(detail_dir / f"{prefix}_edge.csv", index=False)

        # NEW DIMENSIONS
        aggregate_full(df, ["market_type", "edge_bucket"]).to_csv(detail_dir / f"{prefix}_market_edge.csv", index=False)

        aggregate_full(df, ["market_type", "side_group", "edge_bucket"]).to_csv(
            detail_dir / f"{prefix}_market_side_edge.csv", index=False
        )

        aggregate_full(df, ["edge_bucket", "odds_bucket"]).to_csv(
            detail_dir / f"{prefix}_edge_odds.csv", index=False
        )

        aggregate_full(df, ["edge_bucket", "kelly_bucket"]).to_csv(
            detail_dir / f"{prefix}_edge_kelly.csv", index=False
        )

# -----------------------
# MAIN
# -----------------------
def run():
    nba = enrich_work(pd.read_csv(INPUT_DIR / "work_nba.csv"))
    ncaab = enrich_work(pd.read_csv(INPUT_DIR / "work_ncaab.csv"))

    build_detail_reports(nba, NBA_DETAIL_DIR, "nba")
    build_detail_reports(ncaab, NCAAB_DETAIL_DIR, "ncaab")

    print("Detailed edge reports complete.")


if __name__ == "__main__":
    run()
