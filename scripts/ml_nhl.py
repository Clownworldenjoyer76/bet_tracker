import pandas as pd
import glob
import os
from pathlib import Path

# Constants
EDGE_NHL = 0.08
INPUT_DIR = Path("docs/win/dump/csvs/cleaned")
OUTPUT_DIR = Path("docs/win/nhl/moneyline")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def to_american(dec):
    """Converts decimal odds to American odds format."""
    if pd.isna(dec) or dec <= 1.01: 
        return ""
    if dec >= 2.0:
        return f"+{int(round((dec - 1.0) * 100))}"
    else:
        return f"{int(round(-100.0 / (dec - 1.0)))}"

def process_nhl_files():
    # Only pull NHL files from the cleaned dump
    files = glob.glob(str(INPUT_DIR / "nhl_*.csv"))
    
    if not files:
        print(f"No NHL files found in {INPUT_DIR}")
        return

    for file_path in files:
        df = pd.read_csv(file_path)
        
        # Exact column names from your headers
        away_prob_col = 'away_team_moneyline_win_prob'
        home_prob_col = 'home_team_moneyline_win_prob'
        
        # 1. Away ML Calculations
        df['away_ml_fair_decimal_odds'] = (1 / df[away_prob_col]).round(2)
        df['away_ml_fair_american_odds'] = df['away_ml_fair_decimal_odds'].apply(to_american)
        
        df['away_ml_acceptable_decimal_odds'] = (df['away_ml_fair_decimal_odds'] * (1.0 + EDGE_NHL)).round(2)
        df['away_ml_acceptable_american_odds'] = df['away_ml_acceptable_decimal_odds'].apply(to_american)
        
        # 2. Home ML Calculations
        df['home_ml_fair_decimal_odds'] = (1 / df[home_prob_col]).round(2)
        df['home_ml_fair_american_odds'] = df['home_ml_fair_decimal_odds'].apply(to_american)
        
        df['home_ml_acceptable_decimal_odds'] = (df['home_ml_fair_decimal_odds'] * (1.0 + EDGE_NHL)).round(2)
        df['home_ml_acceptable_american_odds'] = df['home_ml_acceptable_decimal_odds'].apply(to_american)
        
        # 3. Cleanup old columns
        cols_to_drop = ['fair_decimal_odds', 'fair_american_odds', 'acceptable_decimal_odds', 'acceptable_american_odds']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

        # 4. Construct output filename
        base_name = os.path.basename(file_path)
        output_path = OUTPUT_DIR / f"ml_{base_name}"
        
        # 5. Save file
        df.to_csv(output_path, index=False)
        print(f"Processed: {base_name} -> {output_path}")

if __name__ == "__main__":
    process_nhl_files()
