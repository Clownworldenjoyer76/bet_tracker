import pandas as pd
import glob
import os

def generate_reports():
    results_dir = "docs/win/final_scores/results"
    team_output = "docs/win/final_scores/results/summary_tally.csv"
    market_output = "docs/win/final_scores/results/market_tally.csv"
    
    # Load all individual result files
    files = glob.glob(os.path.join(results_dir, "*_results_NHL.csv"))
    if not files:
        print("No result files found.")
        return

    # Combine all results into one dataframe
    all_data = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    # --- REPORT 1: TEAM TALLY (Existing Logic) ---
    away_stats = all_data[['away_team', 'market_type', 'bet_result']].rename(columns={'away_team': 'team'})
    home_stats = all_data[['home_team', 'market_type', 'bet_result']].rename(columns={'home_team': 'team'})
    combined_teams = pd.concat([away_stats, home_stats], ignore_index=True)
    
    team_tally = combined_teams.groupby(['team', 'market_type', 'bet_result']).size().unstack(fill_value=0)
    for col in ['Win', 'Loss', 'Push']:
        if col not in team_tally.columns: team_tally[col] = 0
    
    team_tally['Win_Pct'] = (team_tally['Win'] / (team_tally['Win'] + team_tally['Loss'])).fillna(0).round(3)
    team_tally.reset_index().to_csv(team_output, index=False)

    # --- REPORT 2: MARKET TALLY (New Logic) ---
    # Group only by market_type and outcome
    market_tally = all_data.groupby(['market_type', 'bet_result']).size().unstack(fill_value=0)
    
    # Ensure all 3 required markets exist in the index
    for m in ['moneyline', 'total', 'puck_line']:
        if m not in market_tally.index:
            market_tally.loc[m] = 0
            
    # Ensure outcome columns exist
    for col in ['Win', 'Loss', 'Push']:
        if col not in market_tally.columns: 
            market_tally[col] = 0
            
    # Calculate Win % for the markets
    market_tally['Win_Pct'] = (market_tally['Win'] / (market_tally['Win'] + market_tally['Loss'])).fillna(0).round(3)
    
    # Filter for specifically the 3 requested rows
    market_tally = market_tally.loc[['moneyline', 'total', 'puck_line']]
    market_tally.reset_index().to_csv(market_output, index=False)
    
    print(f"Reports saved: {team_output}, {market_output}")

if __name__ == "__main__":
    generate_reports()
