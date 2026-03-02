import pandas as pd
import os

def check_nhl_bets(date_str):
    # Construct Paths
    scores_path = f"docs/win/final_scores/{date_str}_final_scores_NHL.csv"
    bets_path = f"docs/win/hockey/04_select/{date_str}_NHL.csv"
    output_dir = "docs/win/final_scores/results"
    output_path = f"{output_dir}/{date_str}_results_NHL.csv"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    try:
        scores = pd.read_csv(scores_path)
        bets = pd.read_csv(bets_path)
    except FileNotFoundError as e:
        return f"Error: File not found. {e}"

    # Merge bets and scores
    df = pd.merge(bets, scores, on=['away_team', 'home_team', 'game_date'], suffixes=('', '_scorefile'))

    def determine_outcome(row):
        m_type = row['market_type']
        side = row['bet_side']
        line = row['line']
        away, home = row['away_score'], row['home_score']
        total = away + home

        # Total Logic
        if m_type == 'total':
            if side == 'under':
                return 'Win' if total < line else ('Push' if total == line else 'Loss')
            return 'Win' if total > line else ('Push' if total == line else 'Loss')

        # Moneyline Logic
        if m_type == 'moneyline':
            if side == 'away':
                return 'Win' if away > home else 'Loss'
            return 'Win' if home > away else 'Loss'

        # Spread / Puck Line Logic
        if m_type in ['spread', 'puck_line']:
            if side == 'away':
                diff = (away + line) - home
                return 'Win' if diff > 0 else ('Push' if diff == 0 else 'Loss')
            diff = (home + line) - away
            return 'Win' if diff > 0 else ('Push' if diff == 0 else 'Loss')

        return 'Unknown'

    # Apply calculation
    df['bet_result'] = df.apply(determine_outcome, axis=1)

    # Final Output selection
    output_cols = [
        'game_date', 'away_team', 'home_team', 'market_type', 'bet_side', 
        'line', 'away_score', 'home_score', 'bet_result'
    ]
    results_df = df[output_cols]
    
    # Save to file
    results_df.to_csv(output_path, index=False)
    return f"Success: Saved to {output_path}"

# Example usage for the provided date
print(check_nhl_bets("2026_03_01"))
