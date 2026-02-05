import pandas as pd
import glob
import sys
import re
from pathlib import Path

TOLERANCE = 0.005
NEAR_MISS_MAX = TOLERANCE

DK_BASE = "docs/win/manual/normalized"
JUICE_BASE = "docs/win/juice"
FINAL_BASE = "docs/win/final"

DEBUG = "--debug" in sys.argv

def log(msg):
    if DEBUG:
        print(msg)

def american_to_decimal(odds):
    if pd.isna(odds):
        return None
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))

def juice_to_decimal(x):
    if pd.isna(x):
        return None
    try:
        x = float(x)
    except Exception:
        return None
    if abs(x) >= 100:
        return american_to_decimal(x)
    return x

def extract_date_from_filename(path):
    m = re.search(r"(\d{4}_\d{2}_\d{2})", path)
    return m.group(1) if m else None

def load_csvs(pattern):
    files = glob.glob(pattern)
    rows = []
    dates = set()

    for f in files:
        df = pd.read_csv(f)
        date = extract_date_from_filename(f)
        if date:
            df["file_date"] = date
            dates.add(date)
        rows.append(df)

    if not rows:
        return pd.DataFrame(), None

    return pd.concat(rows, ignore_index=True), max(dates) if dates else None

def match_games(dk, juice):
    merged_home = dk.merge(
        juice,
        left_on=["league", "team", "opponent"],
        right_on=["league", "home_team", "away_team"],
        how="inner"
    )

    merged_away = dk.merge(
        juice,
        left_on=["league", "team", "opponent"],
        right_on=["league", "away_team", "home_team"],
        how="inner"
    )

    return pd.concat([merged_home, merged_away], ignore_index=True)

def select_cols(df):
    return df[
        [
            "file_date",
            "league",
            "market",
            "away_team",
            "home_team",
            "bet_side",
            "line",
            "dk_decimal_odds",
            "juice_decimal_odds",
            "edge_decimal_diff",
        ]
    ]

edges = []
near_misses = []
dates_seen = set()
leagues = ["nba", "ncaab", "nhl"]

# ================= MAIN LOOP =================
for league in leagues:

    # ---------- MONEYLINE ----------
    dk, dk_date = load_csvs(f"{DK_BASE}/norm_dk_{league}_moneyline_*.csv")
    juice, juice_date = load_csvs(f"{JUICE_BASE}/{league}/ml/juice_{league}_ml_*.csv")

    if dk.empty or juice.empty:
        continue

    dates_seen.update([dk_date, juice_date])

    merged = match_games(dk, juice)

    for side, team_col, juice_col in [
        ("home", "home_team", "home_ml_juice_odds"),
        ("away", "away_team", "away_ml_juice_odds"),
    ]:
        sub = merged[merged["team"] == merged[team_col]].copy()
        sub["juice_decimal_odds"] = sub[juice_col].apply(juice_to_decimal)
        sub["dk_decimal_odds"] = sub["decimal_odds"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

        edges_sub = sub[sub["edge_decimal_diff"] > TOLERANCE]
        near_sub = sub[(sub["edge_decimal_diff"] > 0) & (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)]

        for df, bucket in [(edges_sub, edges), (near_sub, near_misses)]:
            if not df.empty:
                df["market"] = "ml"
                df["bet_side"] = side
                df["line"] = None
                bucket.append(select_cols(df))

    # ---------- SPREADS ----------
    dk, dk_date = load_csvs(f"{DK_BASE}/norm_dk_{league}_spreads_*.csv")
    juice, juice_date = load_csvs(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")

    if dk.empty or juice.empty:
        continue

    dates_seen.update([dk_date, juice_date])

    merged = match_games(dk, juice)

    for side in ["home", "away"]:
        spread_col = f"{side}_spread"
        juice_col = f"{side}_spread_juice_odds"

        sub = merged[
            (merged["team"] == merged[f"{side}_team"]) &
            (merged["spread"] == merged[spread_col])
        ].copy()

        sub["juice_decimal_odds"] = sub[juice_col].apply(juice_to_decimal)
        sub["dk_decimal_odds"] = sub["decimal_odds"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

        edges_sub = sub[sub["edge_decimal_diff"] > TOLERANCE]
        near_sub = sub[(sub["edge_decimal_diff"] > 0) & (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)]

        for df, bucket in [(edges_sub, edges), (near_sub, near_misses)]:
            if not df.empty:
                df["market"] = "spreads"
                df["bet_side"] = side
                df["line"] = sub["spread"]
                bucket.append(select_cols(df))

# ================= OUTPUT =================
final_df = pd.concat(edges, ignore_index=True) if edges else pd.DataFrame()
near_df = pd.concat(near_misses, ignore_index=True) if near_misses else pd.DataFrame()

if final_df.empty and near_df.empty:
    print("No edges or near misses found.")
    sys.exit(0)

date = max(d for d in dates_seen if d)

Path(FINAL_BASE).mkdir(parents=True, exist_ok=True)

final_df.to_csv(f"{FINAL_BASE}/edges_{date}.csv", index=False)
near_df.to_csv(f"{FINAL_BASE}/near_miss_{date}.csv", index=False)

for league in final_df["league"].unique():
    Path(f"{FINAL_BASE}/{league}").mkdir(parents=True, exist_ok=True)
    final_df[final_df["league"] == league].to_csv(
        f"{FINAL_BASE}/{league}/edges_{league}_{date}.csv",
        index=False,
    )

print(f"Edges written for date {date}")
if DEBUG:
    print(f"Total edges: {len(final_df)}")
    print(f"Near misses: {len(near_df)}")
