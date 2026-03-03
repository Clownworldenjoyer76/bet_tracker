import pandas as pd
import glob
import os

def generate_reports():
    # Define the sports and their specific configurations
    sports_config = [
        {"name": "nhl", "suffix": "NHL", "markets": ['moneyline', 'total', 'puck_line']},
        {"name": "nba", "suffix": "NBA", "markets": ['moneyline', 'total', 'spread']},
        {"name": "ncaab", "suffix": "NCAAB", "markets": ['moneyline', 'total', 'spread']}
    ]

    for sport in sports_config:
        sport_name = sport["name"]
        suffix = sport["suffix"]
        required_markets = sport["markets"]

        results_dir = f"docs/win/final_scores/results/{sport_name}/graded"
        output_base = f"docs/win/final_scores/results/{sport_name}"
        
        team_output = os.path.join(output_base, "summary_tally.csv")
        market_output = os.path.join(output_base, "market_tally.csv")
        
        os.makedirs(output_base, exist_ok=True)
        
        # Find files for this specific sport
        files = glob.glob(os.path.join(results_dir, f"*_results_{suffix}.csv"))
        if not files:
            print(f"No files found for {suffix} in {results_dir}")
            continue

        all_data = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

        # --- REPORT 1: TEAM TALLY ---
        away_stats = all_data[['away_team', 'market_type', 'bet_result']].rename(columns={'away_team': 'team'})
        home_stats = all_data[['home_team', 'market_type', 'bet_result']].rename(columns={'home_team': 'team'})
        combined_teams = pd.concat([away_stats, home_stats], ignore_index=True)
        
        team_tally = combined_teams.groupby(['team', 'market_type', 'bet_result']).size().unstack(fill_value=0)
        for col in ['Win', 'Loss', 'Push']:
            if col not in team_tally.columns: team_tally[col] = 0
        
        team_tally['Total'] = team_tally['Win'] + team_tally['Loss'] + team_tally['Push']
        team_tally['Win_Pct'] = (team_tally['Win'] / team_tally['Total']).fillna(0).round(3)
        
        team_tally = team_tally[['Win', 'Loss', 'Push', 'Total', 'Win_Pct']].reset_index()
        team_tally.to_csv(team_output, index=False)

        # --- REPORT 2: MARKET TALLY ---
        market_tally = all_data.groupby(['market_type', 'bet_result']).size().unstack(fill_value=0)
        
        # Ensure specific sport markets exist in index
        for m in required_markets:
            if m not in market_tally.index: market_tally.loc[m] = 0
            
        # Ensure all result columns exist
        for col in ['Win', 'Loss', 'Push']:
            if col not in market_tally.columns: market_tally[col] = 0
                
        market_tally['Total'] = market_tally['Win'] + market_tally['Loss'] + market_tally['Push']
        market_tally['Win_Pct'] = (market_tally['Win'] / market_tally['Total']).fillna(0).round(3)
        
        # Reorder based on sport-specific markets
        market_tally = market_tally.loc[required_markets, ['Win', 'Loss', 'Push', 'Total', 'Win_Pct']].reset_index()
        market_tally.to_csv(market_output, index=False)
        
        print(f"Reports saved for {suffix} to {output_base}/")

if __name__ == "__main__":
    generate_reports()
