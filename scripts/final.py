import pandas as pd
import glob
import os
import sys
from pathlib import Path

TOLERANCE = 0.005

DK_BASE = "docs/win/manual/normalized"
JUICE_BASE = "docs/win/juice"
FINAL_BASE = "docs/win/final"

def extract_date_from_filename(path):
    return os.path.basename(path).split("_")[-1].replace(".csv", "")

def ensure_single_date(dates):
    if len(dates) != 1:
        raise ValueError(f"Expected exactly one date, found: {dates}")
    return dates.pop()

def load_csvs(pattern):
    files = glob.glob(pattern)
    if not files:
        return pd.DataFrame(), set()
    dfs = []
    dates = set()
    for f in files:
        dates.add(extract_date_from_filename(f))
        dfs.append(pd.read_csv(f))
    return pd.concat(dfs, ignore_index=True), dates

edges = []
all_dates = set()

leagues = ["nba", "ncaab", "nhl"]

# ---------------- MONEYLINE ----------------
for league in leagues:
    dk_df, dk_dates = load_csvs(f"{DK_BASE}/norm_dk_{league}_moneyline_*.csv")
    juice_df, juice_dates = load_csvs(f"{JUICE_BASE}/{league}/ml/juice_{league}_ml_*.csv")

    if dk_df.empty or juice_df.empty:
        continue

    all_dates |= dk_dates | juice_dates

    merged = dk_df.merge(
        juice_df,
        left_on=["league", "date", "time"],
        right_on=["league", "date", "time"],
        how="inner"
    )

    for side, team_col, juice_col in [
        ("home", "home_team", "home_ml_juice_odds"),
        ("away", "away_team", "away_ml_juice_odds"),
    ]:
        mask = merged["team"] == merged[team_col]
        sub = merged[mask].copy()

        sub["juice_decimal_odds"] = sub[juice_col]

        edge_mask = sub["juice_decimal_odds"] > sub["decimal_odds"] + TOLERANCE
        sub = sub[edge_mask]

        sub["market"] = "ml"
        sub["bet_side"] = side
        sub["line"] = None
        sub["dk_decimal_odds"] = sub["decimal_odds"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]
        sub["source_file"] = f"norm_dk_{league}_moneyline"

        edges.append(sub)

# ---------------- SPREADS ----------------
for league in leagues:
    dk_df, dk_dates = load_csvs(f"{DK_BASE}/norm_dk_{league}_spreads_*.csv")
    juice_df, juice_dates = load_csvs(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")

    if dk_df.empty or juice_df.empty:
        continue

    all_dates |= dk_dates | juice_dates

    merged = dk_df.merge(
        juice_df,
        on=["league", "date", "time"],
        how="inner"
    )

    for side in ["home", "away"]:
        spread_col = f"{side}_spread"
        juice_col = f"{side}_spread_juice_odds"

        mask = (
            (merged["team"] == merged[f"{side}_team"]) &
            (merged["spread"] == merged[spread_col])
        )

        sub = merged[mask].copy()

        sub["juice_decimal_odds"] = sub[juice_col]

        edge_mask = sub["juice_decimal_odds"] > sub["decimal_odds"] + TOLERANCE
        sub = sub[edge_mask]

        sub["market"] = "spreads"
        sub["bet_side"] = side
        sub["line"] = sub["spread"]
        sub["dk_decimal_odds"] = sub["decimal_odds"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]
        sub["source_file"] = f"norm_dk_{league}_spreads"

        edges.append(sub)

# ---------------- TOTALS ----------------
for league in leagues:
    dk_df, dk_dates = load_csvs(f"{DK_BASE}/norm_dk_{league}_totals_*.csv")
    juice_df, juice_dates = load_csvs(
        f"{JUICE_BASE}/{league}/totals/juice_{league}_totals_*.csv"
    )

    if dk_df.empty or juice_df.empty:
        continue

    # normalize league (nba_ou -> nba)
    juice_df["league"] = juice_df["league"].str.replace("_ou", "", regex=False)

    all_dates |= dk_dates | juice_dates

    merged = dk_df.merge(
        juice_df,
        left_on=["league", "date", "time", "total"],
        right_on=["league", "date", "time", "dk_total"],
        how="inner"
    )

    for side, juice_col, dk_col in [
        ("over", "over_juice_odds", "dk_over_odds"),
        ("under", "under_juice_odds", "dk_under_odds"),
    ]:
        mask = merged["side"].str.lower() == side
        sub = merged[mask].copy()

        sub["juice_decimal_odds"] = sub[juice_col]
        sub["dk_decimal_odds"] = sub[dk_col]

        edge_mask = sub["juice_decimal_odds"] > sub["dk_decimal_odds"] + TOLERANCE
        sub = sub[edge_mask]

        sub["market"] = "totals"
        sub["bet_side"] = side
        sub["line"] = sub["total"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]
        sub["source_file"] = f"norm_dk_{league}_totals"

        edges.append(sub)

if not edges:
    print("No edges found.")
    sys.exit(0)

final_df = pd.concat(edges, ignore_index=True)

date = ensure_single_date(all_dates)

final_df = final_df[
    [
        "date",
        "league",
        "market",
        "game_id",
        "time",
        "away_team",
        "home_team",
        "bet_side",
        "line",
        "dk_decimal_odds",
        "juice_decimal_odds",
        "edge_decimal_diff",
        "source_file",
    ]
]

Path(FINAL_BASE).mkdir(parents=True, exist_ok=True)

final_df.to_csv(f"{FINAL_BASE}/edges_{date}.csv", index=False)

for league in final_df["league"].unique():
    league_dir = f"{FINAL_BASE}/{league}"
    Path(league_dir).mkdir(parents=True, exist_ok=True)

    final_df[final_df["league"] == league].to_csv(
        f"{league_dir}/edges_{league}_{date}.csv",
        index=False,
    )

print(f"Edges written for date {date}")
