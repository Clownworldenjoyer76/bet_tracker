import pandas as pd
import glob
import os
from pathlib import Path

# Constants
CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nba/totals")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def process_totals():
    # 1. Get list of cleaned NBA projection files
    projection_files = glob.glob(str(CLEANED_DIR / "nba_*.csv"))
    
    for proj_path in projection_files:
        # Extract date from filename (e.g., nba_2026_02_02.csv -> 2026_02_02)
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_file = NORMALIZED_DIR / f"norm_dk_nba_totals_{date_suffix}.csv"
        
        if not dk_file.exists():
            print(f"Skipping: No matching DK totals file for {date_suffix}")
            continue

        # Load data
        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_file)

        # 2. Process DK Data: Pivot from 4 rows per game to 1 row per game
        # We only need one team's perspective (e.g., Pelicans vs Hornets) 
        # because the Over/Under values are identical for both sides.
        dk_rows = []
        
        # Group by game (date, time, team, opponent)
        # Note: Since there are 4 rows, we drop duplicates based on total/odds to get the unique O/U pair
        grouped = df_dk.groupby(['date', 'time', 'team', 'opponent'])
        
        for names, group in grouped:
            over_row = group[group['side'].str.lower() == 'over']
            under_row = group[group['side'].str.lower() == 'under']
            
            if not over_row.empty and not under_row.empty:
                dk_rows.append({
                    'dk_date': names[0],
                    'dk_team': names[2],
                    'dk_opponent': names[3],
                    'dk_total': over_row.iloc[0]['total'],      # VALUE_1
                    'dk_over_odds': over_row.iloc[0]['odds'],    # VALUE_2
                    'dk_under_odds': under_row.iloc[0]['odds'],  # VALUE_3
                    'over_handle_pct': over_row.iloc[0]['handle_pct'], # VALUE_4
                    'over_bets_pct': over_row.iloc[0]['bets_pct'],     # VALUE_5
                    'under_handle_pct': under_row.iloc[0]['handle_pct'], # VALUE_6
                    'under_bets_pct': under_row.iloc[0]['bets_pct']      # VALUE_7
                })
        
        df_dk_final = pd.DataFrame(dk_rows)

        # 3. Merge Projections with DK Data
        # Match Projection 'away_team' to DK 'team' AND 'home_team' to DK 'opponent'
        merged = pd.merge(
            df_proj, 
            df_dk_final, 
            left_on=['away_team', 'home_team'], 
            right_on=['dk_team', 'dk_opponent'], 
            how='inner'
        )

        if merged.empty:
            print(f"No matches found for {date_suffix}")
            continue

        # 4. Construct Output DataFrame with specific column order
        output_df = pd.DataFrame()
        output_df['game_id'] = merged['game_id']
        output_df['league'] = 'nba_ou'
        output_df['date'] = merged['date']
        output_df['time'] = merged['time']
        output_df['away_team'] = merged['away_team']
        output_df['home_team'] = merged['home_team']
        output_df['away_team_projected_points'] = merged['away_team_projected_points']
        output_df['home_team_projected_points'] = merged['home_team_projected_points']
        output_df['over_handle_pct'] = merged['over_handle_pct']
        output_df['over_bets_pct'] = merged['over_bets_pct']
        output_df['under_handle_pct'] = merged['under_handle_pct']
        output_df['under_bets_pct'] = merged['under_bets_pct']
        output_df['game_projected_points'] = merged['game_projected_points']
        output_df['dk_over_odds'] = merged['dk_over_odds']
        output_df['dk_under_odds'] = merged['dk_under_odds']
        output_df['dk_total'] = merged['dk_total']
        
        # Leave these columns blank as requested
        blank_cols = [
            'over_probability', 'under_probability', 
            'over_acceptable_decimal_odds', 'over_acceptable_american_odds',
            'under_acceptable_decimal_odds', 'under_acceptable_american_odds'
        ]
        for col in blank_cols:
            output_df[col] = ""

        # 5. Save output
        output_filename = f"edge_nba_totals_{date_suffix}.csv"
        output_path = OUTPUT_DIR / output_filename
        output_df.to_csv(output_path, index=False)
        print(f"Saved: {output_path}")

if __name__ == "__main__":
    process_totals()
