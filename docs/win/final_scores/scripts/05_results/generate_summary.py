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
        
        # Output file paths
        team_output = os.path.join(output_base, "summary_tally.csv")
        market_output = os.path.join(output_base, "market_tally.csv")
        txt_output = os.path.join(output_base, "performance_report.txt")
        
        os.makedirs(output_base, exist_ok=True)
        
        # Find graded results files
        files = glob.glob(os.path.join(results_dir, f"*_results_{suffix}.csv"))
        if not files:
            print(f"No files found for {suffix} in {results_dir}")
            continue

        # Load all data for this sport
        all_data = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

        # --- DEDUPLICATION STEP ---
        # Ensures that even if the same bet is in multiple files, it only appears once
        all_data = all_data.drop_duplicates(subset=['game_date', 'away_team', 'home_team', 'market_type', 'bet_side', 'line'])

        # --- REPORT 1: TEAM TALLY (CSV) ---
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

        # --- REPORT 2: MARKET TALLY (CSV) ---
        market_tally = all_data.groupby(['market_type', 'bet_result']).size().unstack(fill_value=0)
        for m in required_markets:
            if m not in market_tally.index: market_tally.loc[m] = 0
        for col in ['Win', 'Loss', 'Push']:
            if col not in market_tally.columns: market_tally[col] = 0
                
        market_tally['Total'] = market_tally['Win'] + market_tally['Loss'] + market_tally['Push']
        market_tally['Win_Pct'] = (market_tally['Win'] / market_tally['Total']).fillna(0).round(3)
        
        # Ensure only the required markets are in the tally
        existing_markets = [m for m in required_markets if m in market_tally.index]
        market_tally = market_tally.loc[existing_markets, ['Win', 'Loss', 'Push', 'Total', 'Win_Pct']].reset_index()
        market_tally.to_csv(market_output, index=False)

        # --- REPORT 3: PERFORMANCE LOG (TXT) ---
        with open(txt_output, "w") as f:
            f.write(f"=== {suffix.upper()} DETAILED PERFORMANCE LOG ===\n")
            f.write(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for market in required_markets:
                market_data = all_data[all_data['market_type'] == market]
                
                f.write(f"--- MARKET: {market.upper()} ---\n")
                if market_data.empty:
                    f.write("No recorded bets for this market.\n\n")
                    continue

                # Detail every game
                for _, row in market_data.sort_values('game_date', ascending=False).iterrows():
                    res = str(row['bet_result']).upper().ljust(5)
                    date = row['game_date']
                    matchup = f"{row['away_team']} @ {row['home_team']}"
                    details = f"Side: {row['bet_side']} ({row['line']})"
                    score = f"Score: {row['away_score']}-{row['home_score']}"
                    
                    f.write(f"[{res}] {date} | {matchup.ljust(45)} | {details.ljust(20)} | {score}\n")

                # Market Summary line
                stats_rows = market_tally[market_tally['market_type'] == market]
                if not stats_rows.empty:
                    stats = stats_rows.iloc[0]
                    f.write(f"\n{market.upper()} SUMMARY: {stats['Win']}W - {stats['Loss']}L - {stats['Push']}P")
                    f.write(f" | Win Rate: {stats['Win_Pct']*100:.1f}%\n")
                f.write("-" * 90 + "\n\n")

        print(f"Reports saved for {suffix} to {output_base}/")

if __name__ == "__main__":
    generate_reports()
