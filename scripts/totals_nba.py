import pandas as pd
import glob
from pathlib import Path
from scipy.stats import poisson

# Constants
CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nba/totals")
EDGE = 0.05

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def to_american(decimal_odds):
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def process_totals():
    projection_files = glob.glob(str(CLEANED_DIR / "nba_*.csv"))
    
    for proj_path in projection_files:
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_file = NORMALIZED_DIR / f"dk_nba_totals_{date_suffix}.csv"
        
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
        merged = pd.merge(df_proj, df_dk_final, left_on=['away_team', 'home_team'], right_on=['dk_team', 'dk_opponent'], how='inner')

        if merged.empty:
            continue

        # Calculations
        merged['under_probability'] = merged.apply(lambda x: poisson.cdf(x['dk_total'] - 0.5, x['game_projected_points']), axis=1)
        merged['over_probability'] = 1 - merged['under_probability']
        
        merged['over_acceptable_decimal_odds'] = (1 / merged['over_probability']) * (1 + EDGE)
        merged['under_acceptable_decimal_odds'] = (1 / merged['under_probability']) * (1 + EDGE)
        
        merged['over_acceptable_american_odds'] = merged['over_acceptable_decimal_odds'].apply(to_american)
        merged['under_acceptable_american_odds'] = merged['under_acceptable_decimal_odds'].apply(to_american)

        # Build Output
        cols = [
            'game_id', 'date', 'time', 'away_team', 'home_team', 
            'away_team_projected_points', 'home_team_projected_points',
            'over_handle_pct', 'over_bets_pct', 'under_handle_pct', 'under_bets_pct',
            'game_projected_points', 'dk_over_odds', 'dk_under_odds', 'dk_total',
            'over_probability', 'under_probability', 'over_acceptable_decimal_odds',
            'over_acceptable_american_odds', 'under_acceptable_decimal_odds', 'under_acceptable_american_odds'
        ]
        
        output_df = merged[cols].copy()
        output_df.insert(1, 'league', 'nba_ou')

        output_path = OUTPUT_DIR / f"ou_nba_{date_suffix}.csv"
        output_df.to_csv(output_path, index=False)
        print(f"Saved: {output_path}")

if __name__ == "__main__":
    process_totals()
