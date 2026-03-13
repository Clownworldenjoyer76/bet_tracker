# docs/win/soccer/scripts/02_juice/apply_juice.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import traceback
import sys
from datetime import datetime

# =========================
# CONFIG & PATHS
# =========================

INPUT_DIR = Path("docs/win/soccer/01_merge/market_model")
OUTPUT_DIR = Path("docs/win/soccer/02_juice")
ERROR_LOG = Path("docs/win/soccer/errors/02_juice/01_apply_juice.txt")

JUICE_MAP = {
    "epl": Path("config/soccer/epl/3way_juice.csv"),
    "laliga": Path("config/soccer/la_liga/3way_juice.csv"),
    "bundesliga": Path("config/soccer/bundesliga/3way_juice.csv"),
    "ligue1": Path("config/soccer/ligue1/3way_juice.csv"),
    "seriea": Path("config/soccer/serie_a/3way_juice.csv"),
}

TARGET_2WAY_JUICE = 1.04  # 4% Overround

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def find_closest_juice(prob, juice_df, side):
    side_df = juice_df[juice_df["side"] == side]
    if side_df.empty:
        raise ValueError(f"No juice data for side {side}")
    closest_idx = (side_df["fair_prob"] - prob).abs().idxmin()
    return side_df.loc[closest_idx]

def get_prob_col(df, side):
    """Checks for {side}_win_prob or {side}_prob"""
    for col in [f"{side}_win_prob", f"{side}_prob"]:
        if col in df.columns: return col
    return None

# =========================
# MARKET BLOCKS
# =========================

def process_3way(df, juice_tables):
    """Applies additive juice from CSV curves for Home/Draw/Away"""
    for side in ["home", "draw", "away"]:
        col = get_prob_col(df, side)
        if not col: continue

        df[f"{side}_adjusted_decimal"] = pd.NA
        
        for idx, row in df.iterrows():
            prob, market = row[col], row["market"]
            if pd.isna(prob) or market not in juice_tables: continue
            
            matched = find_closest_juice(prob, juice_tables[market], side)
            adj_prob = min(prob + matched["extra_juice"], 0.999)
            df.at[idx, f"{side}_adjusted_decimal"] = round(1 / adj_prob, 4)
    return df

def process_totals(df):
    """Applies 4% multiplicative juice for Over/Under 2.5"""
    if "over25_prob" not in df.columns: return df
    
    # Calculate adjusted probabilities with 1.04 overround
    df["over25_adj_prob"] = df["over25_prob"] * TARGET_2WAY_JUICE
    df["under25_adj_prob"] = (1 - df["over25_prob"]) * TARGET_2WAY_JUICE
    
    # Convert to decimal
    df["over25_adjusted_decimal"] = (1 / df["over25_adj_prob"]).round(4)
    df["under25_adjusted_decimal"] = (1 / df["under25_adj_prob"]).round(4)
    
    return df.drop(columns=["over25_adj_prob", "under25_adj_prob"])

def process_btts(df):
    """Applies 4% multiplicative juice for BTTS Yes/No"""
    if "btts_prob" not in df.columns: return df

    df["btts_yes_adj_prob"] = df["btts_prob"] * TARGET_2WAY_JUICE
    df["btts_no_adj_prob"] = (1 - df["btts_prob"]) * TARGET_2WAY_JUICE
    
    df["btts_yes_adjusted_decimal"] = (1 / df["btts_yes_adj_prob"]).round(4)
    df["btts_no_adjusted_decimal"] = (1 / df["btts_no_adj_prob"]).round(4)
    
    return df.drop(columns=["btts_yes_adj_prob", "btts_no_adj_prob"])

# =========================
# CORE
# =========================

def main():
    try:
        input_files = glob.glob(str(INPUT_DIR / "**" / "soccer_*.csv"), recursive=True)
        if not input_files: return

        for file_path in input_files:
            df = pd.read_csv(file_path)
            if "market" not in df.columns: continue

            # Load juice tables for 3-way logic
            juice_tables = {m: pd.read_csv(JUICE_MAP[m]) for m in df["market"].unique() if m in JUICE_MAP}

            # Execute blocks
            df = process_3way(df, juice_tables)
            df = process_totals(df)
            df = process_btts(df)

            df.to_csv(OUTPUT_DIR / Path(file_path).name, index=False)
            
        print(f"Processed {len(input_files)} files.")

    except Exception:
        with open(ERROR_LOG, "a") as log:
            log.write(f"\n{datetime.now()}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
