import pandas as pd
import glob
import os
from pathlib import Path

# Constants
EDGE_NBA = 0.06
INPUT_DIR = Path("docs/win/dump/csvs/cleaned")
OUTPUT_DIR = Path("docs/win/nba/moneyline")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def to_american(dec):
    """Converts decimal odds to American odds format."""
    if dec <= 1.01: 
        return 0
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    else:
        return int(round(-100.0 / (dec - 1.0)))

def process_nba_files():
    # Target only NBA files from the cleaned dump
    files = glob.glob(str(INPUT_DIR / "nba_*.csv"))
    
    if not files:
        print(f"No NBA files found in {INPUT_DIR}")
        return

    for file_path in files:
        df = pd.read_csv(file_path)
        
        # 1. Update Acceptable Decimal Odds (Apply 6% Edge)
        df['acceptable_decimal_odds'] = (df['fair_decimal_odds'] * (1.0 + EDGE_NBA)).round(2)
        
        # 2. Update Acceptable American Odds
        df['acceptable_american_odds'] = df['acceptable_decimal_odds'].apply(to_american)
        
        # 3. Construct output filename (e.g., ml_nba_2026_02_01.csv)
        base_name = os.path.basename(file_path)
        output_path = OUTPUT_DIR / f"ml_{base_name}"
        
        # 4. Save file
        df.to_csv(output_path, index=False)
        print(f"Processed: {base_name} -> {output_path}")

if __name__ == "__main__":
    process_nba_files()
