import pandas as pd
import glob
import os
from pathlib import Path

EDGE_NBA = 0.06
INPUT_DIR = Path("docs/win/dump/csvs/cleaned")
OUTPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def process_files():
    # Matches nba_2026_02_01.csv etc.
    files = glob.glob(str(INPUT_DIR / "nba_*.csv"))
    
    for file_path in files:
        df = pd.read_csv(file_path)
        
        # 1. Calculate Acceptable Decimal Odds (Fair * 1.06)
        df['acceptable_decimal_odds'] = (df['fair_decimal_odds'] * (1.0 + EDGE_NBA)).round(2)
        
        # 2. Re-calculate Acceptable American Odds based on the new Decimal
        def to_american(dec):
            if dec >= 2.0:
                return int(round((dec - 1.0) * 100))
            else:
                return int(round(-100.0 / (dec - 1.0)))
        
        df['acceptable_american_odds'] = df['acceptable_decimal_odds'].apply(to_american)
        
        # 3. Save to Edge folder
        filename = os.path.basename(file_path)
        output_filename = f"edge_{filename}"
        df.to_csv(OUTPUT_DIR / output_filename, index=False)
        print(f"Created {output_filename}")

if __name__ == "__main__":
    process_files()
