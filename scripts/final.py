import pandas as pd
import glob
import sys
from pathlib import Path

TOLERANCE = 0.005

DK_BASE = "docs/win/manual/normalized"
JUICE_BASE = "docs/win/juice"
FINAL_BASE = "docs/win/final"

def american_to_decimal(odds):
    if pd.isna(odds):
        return None
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))

def load_csvs(pattern):
    files = glob.glob(pattern)
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

def match_games(dk, juice):
    """
    Join DK ↔ Juice on:
    league + date + (team/opponent ↔ home/away)
    """
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
leagues = ["nba", "ncaab", "nhl"]

# ================= MONEYLINE =================
for league in leagues:
    dk = load_csvs(f"{DK_BASE}/norm_dk_{league}_moneyline_*.csv")
    juice = load_csvs(f"{JUICE_BASE}/{league}/ml/juice_{league}_ml_*.csv")

    if dk.empty or juice.empty:
        continue

    merged = match_games(dk, juice)

    for side, team_col, juice_col in [
        ("home", "home_team", "home_ml_juice_odds"),
        ("away", "away_team", "away_ml_juice_odds"),
    ]:
        sub = merged[merged["team"] == merged[team_col]].copy()
        sub["juice_decimal_odds"] = sub[juice_col]

        sub = sub[sub["juice_decimal_odds"] > sub["decimal_odds"] + TOLERANCE]

        sub["market"] = "ml"
        sub["bet_side"] = side
        sub["line"] = None
        sub["dk_decimal_odds"] = sub["decimal_odds"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

        edges.append(sub)

# ================= SPREADS =================
for league in leagues:
    dk = load_csvs(f"{DK_BASE}/norm_dk_{league}_spreads_*.csv")
    juice = load_csvs(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")

    if dk.empty or juice.empty:
        continue

    merged = match_games(dk, juice)

    for side in ["home", "away"]:
        spread_col = f"{side}_spread"
        juice_col = f"{side}_spread_juice_odds"

        sub = merged[
            (merged["team"] == merged[f"{side}_team"]) &
            (merged["spread"] == merged[spread_col])
        ].copy()

        sub["juice_decimal_odds"] = sub[juice_col]
        sub = sub[sub["juice_decimal_odds"] > sub["decimal_odds"] + TOLERANCE]

        sub["market"] = "spreads"
        sub["bet_side"] = side
        sub["line"] = sub["spread"]
        sub["dk_decimal_odds"] = sub["decimal_odds"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

        edges.append(sub)

# ================= TOTALS =================
for league in leagues:
    dk = load_csvs(f"{DK_BASE}/norm_dk_{league}_totals_*.csv")
    juice = load_csvs(f"{JUICE_BASE}/{league}/totals/juice_{league}_totals_*.csv")

    if dk.empty or juice.empty:
        continue

    # normalize league (nba_ou → nba)
    juice["league"] = juice["league"].str.replace("_ou", "", regex=False)

    merged = match_games(dk, juice)

    for side in ["over", "under"]:
        sub = merged[merged["side"].str.lower() == side].copy()

        sub["juice_decimal_odds"] = sub[f"{side}_juice_odds"]
        sub["dk_decimal_odds"] = sub[f"dk_{side}_odds"].apply(american_to_decimal)

        sub = sub[sub["juice_decimal_odds"] > sub["dk_decimal_odds"] + TOLERANCE]

        sub["market"] = "totals"
        sub["bet_side"] = side
        sub["line"] = sub["total"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]

        edges.append(sub)

# ================= OUTPUT =================
if not edges:
    print("No edges found.")
    sys.exit(0)

final_df = pd.concat(edges, ignore_index=True)

if final_df.empty:
    print("No edges found after comparisons.")
    sys.exit(0)

# latest valid date in results
date = final_df["date"].sort_values().iloc[-1]
final_df = final_df[final_df["date"] == date]

final_df = final_df[
    [
        "date",
        "league",
        "market",
        "time",
        "away_team",
        "home_team",
        "bet_side",
        "line",
        "dk_decimal_odds",
        "juice_decimal_odds",
        "edge_decimal_diff",
    ]
]

Path(FINAL_BASE).mkdir(parents=True, exist_ok=True)
final_df.to_csv(f"{FINAL_BASE}/edges_{date}.csv", index=False)

for league in final_df["league"].unique():
    Path(f"{FINAL_BASE}/{league}").mkdir(parents=True, exist_ok=True)
    final_df[final_df["league"] == league].to_csv(
        f"{FINAL_BASE}/{league}/edges_{league}_{date}.csv",
        index=False,
    )

print(f"Edges written for date {date}")
