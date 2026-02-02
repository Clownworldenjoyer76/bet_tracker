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
    if dec <= 1.01: 
        return 0
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    else:
        return int(round(-100.0 / (dec - 1.0)))

def process_nhl_files():
    # Only pull NHL files from the cleaned dump
    files = glob.glob(str(INPUT_DIR / "nhl_*.csv"))
    
    if not files:
        print(f"No NHL files found in {INPUT_DIR}")
        return

    for file_path in files:
        df = pd.read_csv(file_path)
        
        # 1. Update Acceptable Decimal Odds (Apply 8% Edge)
        # We take the pre-existing fair_decimal_odds from your input
        df['acceptable_decimal_odds'] = (df['fair_decimal_odds'] * (1.0 + EDGE_NHL)).round(2)
        
        # 2. Update Acceptable American Odds based on the new Edge Decimal
        df['acceptable_american_odds'] = df['acceptable_decimal_odds'].apply(to_american)
        
        # 3. Construct output filename (e.g., edge_nhl_2026_02_01.csv)
        base_name = os.path.basename(file_path)
        output_path = OUTPUT_DIR / f"edge_{base_name}"
        
        # 4. Save file
        df.to_csv(output_path, index=False)
        print(f"Processed: {base_name} -> {output_path}")

if __name__ == "__main__":
    process_nhl_files()
