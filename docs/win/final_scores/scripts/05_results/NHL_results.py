import pandas as pd
import os
import glob
import re

def process_all_nhl_results():
    scores_dir = "docs/win/final_scores"
    bets_dir = "docs/win/hockey/04_select"
    output_dir = "docs/win/final_scores/results"
    
    os.makedirs(output_dir, exist_ok=True)

    # Get all bet files from the directory
    bet_files = glob.glob(os.path.join(bets_dir, "*_NHL.csv"))
    
    for bet_file in bet_files:
        # Extract date from filename (e.g., 2026_03_01)
        filename = os.path.basename(bet_file)
        date_match = re.search(r"(\d{4}_\d{2}_\d{2})", filename)
        
        if not date_match:
            continue
            
        date_str = date_match.group(1)
        score_file = os.path.join(scores_dir, f"{date_str}_final_scores_NHL.csv")
        output_path = os.path.join(output_dir, f"{date_str}_results_NHL.csv")

        # Skip if scores aren't available yet
        if not os.path.exists(score_file):
            print(f"Skipping {date_str}: Score file not found.")
            continue

        # Load and process
        bets_df = pd.read_csv(bet_file)
        scores_df = pd.read_csv(score_file)
        df = pd.merge(bets_df, scores_df, on=['away_team', 'home_team', 'game_date'], suffixes=('', '_scorefile'))

        def determine_outcome(row):
            m_type, side, line = row['market_type'], row['bet_side'], row['line']
            away, home = row['away_score'], row['home_score']
            total = away + home

            if m_type == 'total':
                return 'Win' if (total < line if side == 'under' else total > line) else ('Push' if total == line else 'Loss')
            if m_type == 'moneyline':
                return 'Win' if (away > home if side == 'away' else home > away) else 'Loss'
            if m_type in ['spread', 'puck_line']:
                diff = (away + line) - home if side == 'away' else (home + line) - away
                return 'Win' if diff > 0 else ('Push' if diff == 0 else 'Loss')
            return 'Unknown'

        df['bet_result'] = df.apply(determine_outcome, axis=1)
        
        # Save output
        output_cols = ['game_date', 'away_team', 'home_team', 'market_type', 'bet_side', 'line', 'away_score', 'home_score', 'bet_result']
        df[output_cols].to_csv(output_path, index=False)
        print(f"Processed: {date_str}")

if __name__ == "__main__":
    process_all_nhl_results()
