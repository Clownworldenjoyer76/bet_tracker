import pandas as pd
import glob
from pathlib import Path

# Constants
CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def process_spreads():
    # 1. Get list of cleaned NCAAB projection files
    projection_files = glob.glob(str(CLEANED_DIR / "ncaab_*.csv"))
    
    for proj_path in projection_files:
        # Extract date suffix
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_file = NORMALIZED_DIR / f"norm_dk_ncaab_spreads_{date_suffix}.csv"
        
        if not dk_file.exists():
            continue

        # Load data
        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_file)

        # 2. Create lookup for DK data (Pivoting 2 rows into 1 conceptually)
        dk_lookup = {}
        for _, row in df_dk.iterrows():
            dk_lookup[(row['team'], row['opponent'])] = row

        # 3. Build the output list
        output_rows = []
        for _, proj in df_proj.iterrows():
            away = proj['away_team']
            home = proj['home_team']
            
            # Match DK data using away/home team names
            away_side = dk_lookup.get((away, home))
            home_side = dk_lookup.get((home, away))
            
            if away_side is not None and home_side is not None:
                row_data = {
                    'game_id': proj['game_id'],
                    'league': 'ncaab_spreads',
                    'date': proj['date'],
                    'time': proj['time'],
                    'away_team': away,
                    'home_team': home,
                    'away_team_projected_points': proj['away_team_projected_points'],
                    'home_team_projected_points': proj['home_team_projected_points'],
                    'game_projected_points': proj['game_projected_points'],
                    
                    # DK Values mapped from your Glossary
                    'away_spread_handle_pct': away_side['handle_pct'], # VALUE_4
                    'away_spread_bets_pct': away_side['bets_pct'],     # VALUE_5
                    'home_spread_handle_pct': home_side['handle_pct'], # VALUE_6
                    'home_spread_bets_pct': home_side['bets_pct'],     # VALUE_7
                    
                    'dk_away_spread_odds': away_side['odds'],          # VALUE_2
                    'dk_home_spread_odds': home_side['odds'],          # VALUE_3
                    
                    # Blank columns
                    'away_spread_probability': "",
                    'home_spread_probability': "",
                    'away_spread_acceptable_decimal_odds': "",
                    'away_spread_acceptable_american_odds': "",
                    'home_spread_acceptable_decimal_odds': "",
                    'home_spread_acceptable_american_odds': ""
                }
                output_rows.append(row_data)

        if not output_rows:
            continue

        # 4. Create DataFrame and Save
        output_df = pd.DataFrame(output_rows)
        output_path = OUTPUT_DIR / f"spreads_ncaab_{date_suffix}.csv"
        output_df.to_csv(output_path, index=False)
        print(f"Saved: {output_path}")

if __name__ == "__main__":
    process_spreads()
