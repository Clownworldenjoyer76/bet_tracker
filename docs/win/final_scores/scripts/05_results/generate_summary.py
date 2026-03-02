import pandas as pd
import glob
import os

def generate_tally_report():
    results_dir = "docs/win/final_scores/results"
    output_path = "docs/win/final_scores/results/summary_tally.csv"
    
    # Load all result CSVs
    files = glob.glob(os.path.join(results_dir, "*_results_NHL.csv"))
    
    if not files:
        print("No result files found.")
        return

    all_results = [pd.read_csv(f) for f in files]
    df = pd.concat(all_results, ignore_index=True)

    # Group and count the bet_result column
    tally = df.groupby(['away_team', 'home_team', 'market_type', 'bet_result']).size().unstack(fill_value=0)

    # Ensure Win, Loss, and Push columns exist
    for col in ['Win', 'Loss', 'Push']:
        if col not in tally.columns:
            tally[col] = 0

    # Calculate standard win percentage (Wins / Total Decided Games)
    tally['Win_Pct'] = (tally['Win'] / (tally['Win'] + tally['Loss'])).fillna(0).round(3)

    # Clean up and save
    tally = tally.reset_index()
    tally.to_csv(output_path, index=False)
    
    print(f"Summary report saved to {output_path}")
    print(tally)

if __name__ == "__main__":
    generate_tally_report()
