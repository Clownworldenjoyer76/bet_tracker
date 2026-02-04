import pandas as pd
import glob
import os
import sys
import re
from pathlib import Path
from datetime import datetime

TOLERANCE = 0.005

DK_BASE = "docs/win/manual/normalized"
JUICE_BASE = "docs/win/juice"
FINAL_BASE = "docs/win/final"

# ---------- helpers ----------

def american_to_decimal(odds):
    if pd.isna(odds):
        return None
    if odds > 0:
        return 1 + (odds / 100)
    else:
        return 1 + (100 / abs(odds))

def extract_date_from_filename(path):
    name = os.path.basename(path)

    m1 = re.search(r"(20\d{2}_\d{2}_\d{2})", name)
    if m1:
        return m1.group(1)

    m2 = re.search(r"(20\d{6})", name)
    if m2:
        raw = m2.group(1)
        return f"{raw[:4]}_{raw[4:6]}_{raw[6:8]}"

    raise ValueError(f"No date found in filename: {name}")

def select_latest_date(dates):
    parsed = {d: datetime.strptime(d, "%Y_%m_%d") for d in dates}
    return max(parsed, key=parsed.get)

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

# ---------- main ----------

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
        sub = merged[merged["team"] == merged[team_col]].copy()
        sub["juice_decimal_odds"] = sub[juice_col]

        sub = sub[sub["juice_decimal_odds"] > sub["decimal_odds"] + TOLERANCE]

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
        sub = merged[
            (merged["team"] == merged[f"{side}_team"]) &
            (merged["spread"] == merged[f"{side}_spread"])
        ].copy()

        sub["juice_decimal_odds"] = sub[f"{side}_spread_juice_odds"]
        sub = sub[sub["juice_decimal_odds"] > sub["decimal_odds"] + TOLERANCE]

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

    # normalize league (nba_ou → nba)
    juice_df["league"] = juice_df["league"].str.replace("_ou", "", regex=False)

    all_dates |= dk_dates | juice_dates

    merged = dk_df.merge(
        juice_df,
        left_on=["league", "date", "time", "total"],
        right_on=["league", "date", "time", "dk_total"],
        how="inner"
    )

    for side in ["over", "under"]:
        sub = merged[merged["side"].str.lower() == side].copy()

        sub["juice_decimal_odds"] = sub[f"{side}_juice_odds"]
        sub["dk_decimal_odds"] = sub[f"dk_{side}_odds"].apply(american_to_decimal)

        sub = sub[sub["juice_decimal_odds"] > sub["dk_decimal_odds"] + TOLERANCE]

        sub["market"] = "totals"
        sub["bet_side"] = side
        sub["line"] = sub["total"]
        sub["edge_decimal_diff"] = sub["juice_decimal_odds"] - sub["dk_decimal_odds"]
        sub["source_file"] = f"norm_dk_{league}_totals"

        edges.append(sub)

# ---------------- OUTPUT ----------------
if not edges:
    print("No edges found.")
    sys.exit(0)

final_df = pd.concat(edges, ignore_index=True)

date = select_latest_date(all_dates)
final_df = final_df[final_df["date"] == date]

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
    Path(f"{FINAL_BASE}/{league}").mkdir(parents=True, exist_ok=True)
    final_df[final_df["league"] == league].to_csv(
        f"{FINAL_BASE}/{league}/edges_{league}_{date}.csv",
        index=False,
    )

print(f"Edges written for date {date}")
