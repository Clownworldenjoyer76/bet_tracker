import pandas as pd
import glob
import os

def generate_reports():
    results_dir = "docs/win/final_scores/results"
    team_output = "docs/win/final_scores/results/summary_tally.csv"
    market_output = "docs/win/final_scores/results/market_tally.csv"
    
    files = glob.glob(os.path.join(results_dir, "*_results_NHL.csv"))
    if not files:
        return

    all_data = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    # --- REPORT 1: TEAM TALLY ---
    away_stats = all_data[['away_team', 'market_type', 'bet_result']].rename(columns={'away_team': 'team'})
    home_stats = all_data[['home_team', 'market_type', 'bet_result']].rename(columns={'home_team': 'team'})
    combined_teams = pd.concat([away_stats, home_stats], ignore_index=True)
    
    team_tally = combined_teams.groupby(['team', 'market_type', 'bet_result']).size().unstack(fill_value=0)
    for col in ['Win', 'Loss', 'Push']:
        if col not in team_tally.columns: team_tally[col] = 0
    
    # Add Total and Calculate Win %
    team_tally['Total'] = team_tally['Win'] + team_tally['Loss'] + team_tally['Push']
    team_tally['Win_Pct'] = (team_tally['Win'] / team_tally['Total']).fillna(0).round(3)
    
    # Reorder columns: Win, Loss, Push, Total, Win_Pct
    team_tally = team_tally[['Win', 'Loss', 'Push', 'Total', 'Win_Pct']].reset_index()
    team_tally.to_csv(team_output, index=False)

    # --- REPORT 2: MARKET TALLY ---
    market_tally = all_data.groupby(['market_type', 'bet_result']).size().unstack(fill_value=0)
    
    for m in ['moneyline', 'total', 'puck_line']:
        if m not in market_tally.index: market_tally.loc[m] = 0
    for col in ['Win', 'Loss', 'Push']:
        if col not in market_tally.columns: market_tally[col] = 0
            
    market_tally['Total'] = market_tally['Win'] + market_tally['Loss'] + market_tally['Push']
    market_tally['Win_Pct'] = (market_tally['Win'] / market_tally['Total']).fillna(0).round(3)
    
    # Reorder and filter for the 3 markets
    market_tally = market_tally.loc[['moneyline', 'total', 'puck_line'], ['Win', 'Loss', 'Push', 'Total', 'Win_Pct']].reset_index()
    market_tally.to_csv(market_output, index=False)
    
    print(f"Reports saved. Order: Win, Loss, Push.")

if __name__ == "__main__":
    generate_reports()
