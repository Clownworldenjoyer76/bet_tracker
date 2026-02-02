import pandas as pd
import glob
import numpy as np
from pathlib import Path
from scipy.stats import norm

# Constants
CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
EDGE = 0.05
NCAAB_STD_DEV = 11  # Standard deviation for NCAAB margins

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1.01: return ""
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def process_spreads():
    projection_files = glob.glob(str(CLEANED_DIR / "ncaab_*.csv"))
    
    for proj_path in projection_files:
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_file = NORMALIZED_DIR / f"norm_dk_ncaab_spreads_{date_suffix}.csv"
        
        if not dk_file.exists(): continue

        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_file)
        dk_lookup = {(row['team'], row['opponent']): row for _, row in df_dk.iterrows()}

        output_rows = []
        for _, proj in df_proj.iterrows():
            away, home = proj['away_team'], proj['home_team']
            away_side, home_side = dk_lookup.get((away, home)), dk_lookup.get((home, away))
            
            if away_side is not None and home_side is not None:
                # 1. Calc projected home margin
                proj_margin = proj['home_team_projected_points'] - proj['away_team_projected_points']
                
                # 2. Probability to cover spread
                # norm.cdf(x, mean, std) finds probability of result < x
                home_prob = 1 - norm.cdf(-home_side['spread'], proj_margin, NCAAB_STD_DEV)
                away_prob = 1 - home_prob

                # 3. Fair odds + 5% Edge
                away_dec = (1 / away_prob) * (1 + EDGE) if away_prob > 0.01 else 0
                home_dec = (1 / home_prob) * (1 + EDGE) if home_prob > 0.01 else 0

                output_rows.append({
                    'game_id': proj['game_id'],
                    'league': 'ncaab_spreads',
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
                    'away_spread_probability': round(away_prob, 4),
                    'home_spread_probability': round(home_prob, 4),
                    'away_spread_acceptable_decimal_odds': round(away_dec, 3) if away_dec > 0 else "",
                    'away_spread_acceptable_american_odds': to_american(away_dec),
                    'home_spread_acceptable_decimal_odds': round(home_dec, 3) if home_dec > 0 else "",
                    'home_spread_acceptable_american_odds': to_american(home_dec)
                })

        if output_rows:
            pd.DataFrame(output_rows).to_csv(OUTPUT_DIR / f"spreads_ncaab_{date_suffix}.csv", index=False)

if __name__ == "__main__":
    process_spreads()
