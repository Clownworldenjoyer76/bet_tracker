import pandas as pd
import glob
import sys
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
    # American odds heuristic
    if abs(x) >= 100:
        return american_to_decimal(x)
    return x

def safe_date_for_filename(date_str):
    return (
        str(date_str)
        .replace("/", "_")
        .replace("-", "_")
        .strip()
    )

def load_csvs(pattern):
    files = glob.glob(pattern)
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

def match_games(dk, juice):
    merged_home = dk.merge(
        juice,
        left_on=["league", "date", "team", "opponent"],
        right_on=["league", "date", "home_team", "away_team"],
        how="inner"
    )

    merged_away = dk.merge(
        juice,
        left_on=["league", "date", "team", "opponent"],
        right_on=["league", "date", "away_team", "home_team"],
        how="inner"
    )

    return pd.concat([merged_home, merged_away], ignore_index=True)

edges = []
near_misses = []
leagues = ["nba", "ncaab", "nhl"]

# ================= MAIN LOOP =================
for league in leagues:
    log(f"\n=== {league.upper()} ===")

    # ---------- MONEYLINE ----------
    dk = load_csvs(f"{DK_BASE}/norm_dk_{league}_moneyline_*.csv")
    juice = load_csvs(f"{JUICE_BASE}/{league}/ml/juice_{league}_ml_*.csv")

    log(f"ML DK rows: {len(dk)}, Juice rows: {len(juice)}")

    if not dk.empty and not juice.empty:
        merged = match_games(dk, juice)
        log(f"ML joined rows: {len(merged)}")

        for side, team_col, juice_col in [
            ("home", "home_team", "home_ml_juice_odds"),
            ("away", "away_team", "away_ml_juice_odds"),
        ]:
            sub = merged[merged["team"] == merged[team_col]].copy()
            sub["juice_decimal_odds"] = sub[juice_col].apply(juice_to_decimal)
            sub["dk_decimal_odds"] = sub["decimal_odds"]
            sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

            edges_sub = sub[sub["edge_decimal_diff"] > TOLERANCE]
            near_sub = sub[
                (sub["edge_decimal_diff"] > 0) &
                (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)
            ]

            if not edges_sub.empty:
                edges_sub["market"] = "ml"
                edges_sub["bet_side"] = side
                edges_sub["line"] = None
                edges.append(edges_sub)

            if not near_sub.empty:
                near_sub["market"] = "ml"
                near_sub["bet_side"] = side
                near_misses.append(near_sub)

    # ---------- SPREADS ----------
    dk = load_csvs(f"{DK_BASE}/norm_dk_{league}_spreads_*.csv")
    juice = load_csvs(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")

    log(f"Spreads DK rows: {len(dk)}, Juice rows: {len(juice)}")

    if not dk.empty and not juice.empty:
        merged = match_games(dk, juice)
        log(f"Spreads joined rows: {len(merged)}")

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
            near_sub = sub[
                (sub["edge_decimal_diff"] > 0) &
                (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)
            ]

            if not edges_sub.empty:
                edges_sub["market"] = "spreads"
                edges_sub["bet_side"] = side
                edges_sub["line"] = sub["spread"]
                edges.append(edges_sub)

            if not near_sub.empty:
                near_sub["market"] = "spreads"
                near_sub["bet_side"] = side
                near_misses.append(near_sub)

    # ---------- TOTALS ----------
    dk = load_csvs(f"{DK_BASE}/norm_dk_{league}_totals_*.csv")
    juice = load_csvs(f"{JUICE_BASE}/{league}/totals/juice_{league}_totals_*.csv")

    log(f"Totals DK rows: {len(dk)}, Juice rows: {len(juice)}")

    if not dk.empty and not juice.empty:
        juice["league"] = juice["league"].str.replace("_ou", "", regex=False)
        merged = match_games(dk, juice)
        log(f"Totals joined rows: {len(merged)}")

        for side in ["over", "under"]:
            sub = merged[merged["side"].str.lower() == side].copy()
            sub["juice_decimal_odds"] = sub[f"{side}_juice_odds"].apply(juice_to_decimal)
            sub["dk_decimal_odds"] = sub[f"dk_{side}_odds"].apply(american_to_decimal)
            sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

            edges_sub = sub[sub["edge_decimal_diff"] > TOLERANCE]
            near_sub = sub[
                (sub["edge_decimal_diff"] > 0) &
                (sub["edge_decimal_diff"] <= NEAR_MISS_MAX)
            ]

            if not edges_sub.empty:
                edges_sub["market"] = "totals"
                edges_sub["bet_side"] = side
                edges_sub["line"] = sub["total"]
                edges.append(edges_sub)

            if not near_sub.empty:
                near_sub["market"] = "totals"
                near_sub["bet_side"] = side
                near_misses.append(near_sub)

# ================= OUTPUT =================
columns = [
    "date",
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

final_df = pd.concat(edges, ignore_index=True) if edges else pd.DataFrame(columns=columns)
near_df = pd.concat(near_misses, ignore_index=True) if near_misses else pd.DataFrame(columns=columns)

# determine date
if not final_df.empty:
    raw_date = final_df["date"].sort_values().iloc[-1]
else:
    dk_dates = []
    for league in leagues:
        dk_tmp = load_csvs(f"{DK_BASE}/norm_dk_{league}_*.csv")
        if not dk_tmp.empty and "date" in dk_tmp.columns:
            dk_dates.append(dk_tmp["date"].max())

    if not dk_dates:
        print("No data available to determine date.")
        sys.exit(0)

    raw_date = max(dk_dates)

safe_date = safe_date_for_filename(raw_date)

final_df = final_df[final_df["date"] == raw_date]
near_df = near_df[near_df["date"] == raw_date]

Path(FINAL_BASE).mkdir(parents=True, exist_ok=True)

final_df.to_csv(f"{FINAL_BASE}/edges_{safe_date}.csv", index=False)
near_df.to_csv(f"{FINAL_BASE}/near_miss_{safe_date}.csv", index=False)

for league in leagues:
    Path(f"{FINAL_BASE}/{league}").mkdir(parents=True, exist_ok=True)
    final_df[final_df["league"] == league].to_csv(
        f"{FINAL_BASE}/{league}/edges_{league}_{safe_date}.csv",
        index=False,
    )

print(f"Edges written for date {safe_date}")
if DEBUG:
    print(f"Total edges: {len(final_df)}")
    print(f"Near misses: {len(near_df)}")
