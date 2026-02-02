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
    projection_files = glob.glob(str(CLEANED_DIR / "nba_*.csv"))
    
    for proj_path in projection_files:
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_file = NORMALIZED_DIR / f"norm_dk_nba_totals_{date_suffix}.csv"
        
        if not dk_file.exists():
            continue

        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_file)

        dk_rows = []
        grouped = df_dk.groupby(['date', 'time', 'team', 'opponent'])
        
        for names, group in grouped:
            over_row = group[group['side'].str.lower() == 'over']
            under_row = group[group['side'].str.lower() == 'under']
            
            if not over_row.empty and not under_row.empty:
                dk_rows.append({
                    'dk_team': names[2],
                    'dk_opponent': names[3],
                    'dk_total': over_row.iloc[0]['total'],
                    'dk_over_odds': over_row.iloc[0]['odds'],
                    'dk_under_odds': under_row.iloc[0]['odds'],
                    'over_handle_pct': over_row.iloc[0]['handle_pct'],
                    'over_bets_pct': over_row.iloc[0]['bets_pct'],
                    'under_handle_pct': under_row.iloc[0]['handle_pct'],
                    'under_bets_pct': under_row.iloc[0]['bets_pct']
                })
        
        df_dk_final = pd.DataFrame(dk_rows)

        merged = pd.merge(
            df_proj, 
            df_dk_final, 
            left_on=['away_team', 'home_team'], 
            right_on=['dk_team', 'dk_opponent'], 
            how='inner'
        )

        if merged.empty:
            continue

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
        
        blank_cols = [
            'over_probability', 'under_probability', 
            'over_acceptable_decimal_odds', 'over_acceptable_american_odds',
            'under_acceptable_decimal_odds', 'under_acceptable_american_odds'
        ]
        for col in blank_cols:
            output_df[col] = ""

        # UPDATED FILENAME
        output_path = OUTPUT_DIR / "ou_nba.csv"
        output_df.to_csv(output_path, index=False)
        print(f"Saved: {output_path}")

if __name__ == "__main__":
    process_totals()
