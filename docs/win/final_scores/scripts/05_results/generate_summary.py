import pandas as pd
import glob
import os

def generate_tally_report():
    results_dir = "docs/win/final_scores/results"
    output_path = "docs/win/final_scores/results/summary_tally.csv"
    
    files = glob.glob(os.path.join(results_dir, "*_results_NHL.csv"))
    # Exclude the summary file itself to prevent recursive reading
    files = [f for f in files if "summary_tally.csv" not in f]
    
    if not files:
        print("No result files found.")
        return

    all_results = [pd.read_csv(f) for f in files]
    df = pd.concat(all_results, ignore_index=True)

    # Reshape: Combine away_team and home_team into a single 'team' column
    away_stats = df[['away_team', 'market_type', 'bet_result']].rename(columns={'away_team': 'team'})
    home_stats = df[['home_team', 'market_type', 'bet_result']].rename(columns={'home_team': 'team'})
    combined = pd.concat([away_stats, home_stats])

    # Group by team and market_type
    tally = combined.groupby(['team', 'market_type', 'bet_result']).size().unstack(fill_value=0)

    # Ensure Win, Loss, and Push columns exist
    for col in ['Win', 'Loss', 'Push']:
        if col not in tally.columns:
            tally[col] = 0

    # Calculate Win %
    tally['Win_Pct'] = (tally['Win'] / (tally['Win'] + tally['Loss'])).fillna(0).round(3)
    tally = tally.reset_index()

    tally.to_csv(output_path, index=False)
    print(f"Summary report saved to {output_path}")

if __name__ == "__main__":
    generate_tally_report()
