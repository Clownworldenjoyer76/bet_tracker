import pandas as pd
import glob
import os
from pathlib import Path

# Constants
EDGE_NCAAB = 0.05
INPUT_DIR = Path("docs/win/dump/csvs/cleaned")
OUTPUT_DIR = Path("docs/win/ncaab/moneyline")

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

def process_ncaab_files():
    files = glob.glob(str(INPUT_DIR / "ncaab_*.csv"))
    
    if not files:
        print(f"No NCAAB files found in {INPUT_DIR}")
        return

    for file_path in files:
        df = pd.read_csv(file_path)
        
        # 1. Away ML Calculations
        # Fair = 1 / Probability
        df['away_ml_fair_decimal_odds'] = (1 / df['away_win_probability']).round(2)
        df['away_ml_fair_american_odds'] = df['away_ml_fair_decimal_odds'].apply(to_american)
        
        # Acceptable = Fair * (1 + Edge)
        df['away_ml_acceptable_decimal_odds'] = (df['away_ml_fair_decimal_odds'] * (1.0 + EDGE_NCAAB)).round(2)
        df['away_ml_acceptable_american_odds'] = df['away_ml_acceptable_decimal_odds'].apply(to_american)
        
        # 2. Home ML Calculations
        df['home_ml_fair_decimal_odds'] = (1 / df['home_win_probability']).round(2)
        df['home_ml_fair_american_odds'] = df['home_ml_fair_decimal_odds'].apply(to_american)
        
        # Acceptable = Fair * (1 + Edge)
        df['home_ml_acceptable_decimal_odds'] = (df['home_ml_fair_decimal_odds'] * (1.0 + EDGE_NCAAB)).round(2)
        df['home_ml_acceptable_american_odds'] = df['home_ml_acceptable_decimal_odds'].apply(to_american)
        
        # 3. Drop the old ambiguous columns if they exist
        cols_to_drop = ['fair_decimal_odds', 'fair_american_odds', 'acceptable_decimal_odds', 'acceptable_american_odds']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

        # 4. Construct output filename
        base_name = os.path.basename(file_path)
        output_path = OUTPUT_DIR / f"ml_{base_name}"
        
        # 5. Save file
        df.to_csv(output_path, index=False)
        print(f"Processed: {base_name} -> {output_path}")

if __name__ == "__main__":
    process_ncaab_files()
