import pandas as pd
import glob
import numpy as np
from pathlib import Path
from scipy.stats import norm

# Constants
CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nba/spreads")
EDGE = 0.05
NBA_STD_DEV = 12  # Standard deviation for NBA margins

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1.0:
        return ""
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def process_spreads():
    projection_files = glob.glob(str(CLEANED_DIR / "nba_*.csv"))
    
    for proj_path in projection_files:
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_file = NORMALIZED_DIR / f"norm_dk_nba_spreads_{date_suffix}.csv"
        
        if not dk_file.exists():
            continue

        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_file)

        # Create lookup: (team, opponent) -> row
        dk_lookup = {(row['team'], row['opponent']): row for _, row in df_dk.iterrows()}

        output_rows = []
        for _, proj in df_proj.iterrows():
            away, home = proj['away_team'], proj['home_team']
            away_side = dk_lookup.get((away, home))
            home_side = dk_lookup.get((home, away))
            
            if away_side is not None and home_side is not None:
                # 1. Calculate Projected Home Margin (Home - Away)
                proj_home_margin = proj['home_team_projected_points'] - proj['away_team_projected_points']
                
                # 2. Probability Home covers (Home Margin + Home Spread > 0)
                # Note: spread is usually negative for favorites (e.g., -6.5)
                home_prob = 1 - norm.cdf(-home_side['spread'], proj_home_margin, NBA_STD_DEV)
                away_prob = 1 - home_prob

                # 3. Calculate Acceptable Odds with 5% Edge
                away_dec = (1 / away_prob) * (1 + EDGE) if away_prob > 0 else np.nan
                home_dec = (1 / home_prob) * (1 + EDGE) if home_prob > 0 else np.nan

                output_rows.append({
                    'game_id': proj['game_id'],
                    'league': 'nba_spreads',
                    'date': proj['date'],
                    'time': proj['time'],
                    'away_team': away,
                    'home_team': home,
                    'away_team_projected_points': proj['away_team_projected_points'],
                    'home_team_projected_points': proj['home_team_projected_points'],
                    'game_projected_points': proj['game_projected_points'],
                    'away_spread': away_side['spread'],
                    'home_spread': home_side['spread'],
                    'away_spread_handle_pct': away_side['handle_pct'],
                    'away_spread_bets_pct': away_side['bets_pct'],
                    'home_spread_handle_pct': home_side['handle_pct'],
                    'home_spread_bets_pct': home_side['bets_pct'],
                    'dk_away_spread_odds': away_side['odds'],
                    'dk_home_spread_odds': home_side['odds'],
                    
                    # New Calculated Columns
                    'away_spread_probability': round(away_prob, 4),
                    'home_spread_probability': round(home_prob, 4),
                    'away_spread_acceptable_decimal_odds': round(away_dec, 3),
                    'away_spread_acceptable_american_odds': to_american(away_dec),
                    'home_spread_acceptable_decimal_odds': round(home_dec, 3),
                    'home_spread_acceptable_american_odds': to_american(home_dec)
                })

        if output_rows:
            output_df = pd.DataFrame(output_rows)
            output_path = OUTPUT_DIR / f"spreads_nba_{date_suffix}.csv"
            output_df.to_csv(output_path, index=False)
            print(f"Saved: {output_path}")

if __name__ == "__main__":
    process_spreads()
