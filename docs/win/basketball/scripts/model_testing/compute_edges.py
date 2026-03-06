import pandas as pd
from pathlib import Path
import re

INPUT_DIR = Path("docs/win/basketball/02_processed")
OUTPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_date(filename):
    match = re.search(r"(\d{4}_\d{2}_d{2})", filename)
    return match.group(1) if match else "0000_00_00"

def compute_total_edges(df):
    if df.empty: return df
    df["total_projected_points"] = df["home_projected_points"] + df["away_projected_points"]
    df["total_std"] = abs(df["total_projected_points"] - df["total"])
    df["over_edge"] = (df["total_projected_points"] - df["total"]) / df["total"]
    df["under_edge"] = (df["total"] - df["total_projected_points"]) / df["total"]
    df["edge"] = df[["over_edge", "under_edge"]].max(axis=1)
    df["bet_side"] = df.apply(lambda x: "OVER" if x["over_edge"] > x["under_edge"] else "UNDER", axis=1)
    return df

def compute_spread_edges(df):
    if df.empty: return df
    df["projected_margin"] = df["home_projected_points"] - df["away_projected_points"]
    df["spread_std"] = abs(df["projected_margin"] + df["home_spread"])
    df["home_edge"] = (df["projected_margin"] + df["home_spread"]) / 100
    df["away_edge"] = -(df["projected_margin"] + df["home_spread"]) / 100
    df["edge"] = df[["home_edge", "away_edge"]].max(axis=1)
    df["bet_side"] = df.apply(lambda x: "HOME" if x["home_edge"] > x["away_edge"] else "AWAY", axis=1)
    return df

def compute_ml_edges(df):
    if df.empty: return df
    def get_implied(odds):
        if odds > 0: return 100 / (odds + 100)
        return abs(odds) / (abs(odds) + 100)
    
    df["home_implied"] = df["home_ml"].apply(get_implied)
    df["away_implied"] = df["away_ml"].apply(get_implied)
    df["home_edge"] = df["home_prob"] - df["home_implied"]
    df["away_edge"] = df["away_prob"] - df["away_implied"]
    df["edge"] = df[["home_edge", "away_edge"]].max(axis=1)
    df["bet_side"] = df.apply(lambda x: "HOME" if x["home_edge"] > x["away_edge"] else "AWAY", axis=1)
    return df

def process_all():
    mappings = {
        "total": compute_total_edges,
        "spread": compute_spread_edges,
        "moneyline": compute_ml_edges
    }
    for market, func in mappings.items():
        files = list(INPUT_DIR.glob(f"*_basketball_*_{market}.csv"))
        for f in files:
            league = "NBA" if "nba" in f.name.lower() else "NCAAB"
            df = pd.read_csv(f)
            df = func(df)
            date_str = extract_date(f.name)
            df.to_csv(OUTPUT_DIR / f"{date_str}_basketball_{league}_{market}.csv", index=False)

if __name__ == "__main__":
    process_all()
