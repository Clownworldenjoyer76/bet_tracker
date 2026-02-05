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

    return pd.concat(rows, ignore_index=True), max(dates)

def match_games(dk, juice):
    h = dk.merge(
        juice,
        left_on=["league", "team", "opponent"],
        right_on=["league", "home_team", "away_team"],
        how="inner"
    )
    a = dk.merge(
        juice,
        left_on=["league", "team", "opponent"],
        right_on=["league", "away_team", "home_team"],
        how="inner"
    )
    return pd.concat([h, a], ignore_index=True)

def stabilize(df, date):
    df["file_date"] = df.get("file_date", date)
    return df

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

        for df, bucket in [
            (sub[sub["edge_decimal_diff"] > TOLERANCE], edges),
            (sub[(sub["edge_decimal_diff"] > 0) & (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)], near_misses),
        ]:
            if not df.empty:
                df["market"] = "ml"
                df["bet_side"] = side
                df["line"] = None
                bucket.append(select_cols(stabilize(df, dk_date)))

    # ---------- SPREADS ----------
    dk, dk_date = load_csvs(f"{DK_BASE}/norm_dk_{league}_spreads_*.csv")
    juice, juice_date = load_csvs(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")
    if dk.empty or juice.empty:
        continue

    dates_seen.update([dk_date, juice_date])
    merged = match_games(dk, juice)

    for side in ["home", "away"]:
        sub = merged[
            (merged["team"] == merged[f"{side}_team"]) &
            (merged["spread"] == merged[f"{side}_spread"])
        ].copy()

        sub["juice_decimal_odds"] = sub[f"{side}_spread_juice_odds"].apply(juice_to_decimal)
        sub["dk_decimal_odds"] = sub["decimal_odds"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

        for df, bucket in [
            (sub[sub["edge_decimal_diff"] > TOLERANCE], edges),
            (sub[(sub["edge_decimal_diff"] > 0) & (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)], near_misses),
        ]:
            if not df.empty:
                df["market"] = "spreads"
                df["bet_side"] = side
                df["line"] = df["spread"]
                bucket.append(select_cols(stabilize(df, dk_date)))

    # ---------- TOTALS ----------
    dk, dk_date = load_csvs(f"{DK_BASE}/norm_dk_{league}_totals_*.csv")
    juice, juice_date = load_csvs(f"{JUICE_BASE}/{league}/totals/juice_{league}_totals_*.csv")
    if dk.empty or juice.empty:
        continue

    juice["league"] = juice["league"].astype(str).str.replace("_ou", "", regex=False)
    dates_seen.update([dk_date, juice_date])
    merged = match_games(dk, juice)

    for side in ["over", "under"]:
        sub = merged[merged["side"].astype(str).str.lower() == side].copy()
        sub["juice_decimal_odds"] = sub[f"{side}_juice_odds"].apply(juice_to_decimal)
        sub["dk_decimal_odds"] = sub[f"dk_{side}_odds"].apply(american_to_decimal)
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

        for df, bucket in [
            (sub[sub["edge_decimal_diff"] > TOLERANCE], edges),
            (sub[(sub["edge_decimal_diff"] > 0) & (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)], near_misses),
        ]:
            if not df.empty:
                df["market"] = "totals"
                df["bet_side"] = side
                df["line"] = df["total"]
                bucket.append(select_cols(stabilize(df, dk_date)))

# ================= OUTPUT =================
if not edges and not near_misses:
    print("No edges or near misses found.")
    sys.exit(0)

date = max(d for d in dates_seen if d)

final_df = pd.concat(edges, ignore_index=True)
near_df = pd.concat(near_misses, ignore_index=True)

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
    print(f"Edges: {len(final_df)} | Near misses: {len(near_df)}")
