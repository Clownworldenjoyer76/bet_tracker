import os
import pandas as pd
import glob
from datetime import datetime

# Path Setup
INPUT_DIR = "docs/win/dump/csvs/"
OUTPUT_DIR = "docs/win/dump/csvs/cleaned/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def conv_american(dec):
    if dec <= 1: return 0
    if dec >= 2.0:
        return int((dec - 1) * 100)
    else:
        return int(-100 / (dec - 1))

def process_files():
    files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))
    
    for file_path in files:
        filename = os.path.basename(file_path)
        league = filename.split('_')[0].lower()
        
        # Load data - handling potential multiline quotes
        df = pd.read_csv(file_path)
        processed_data = []

        for index, row in df.iterrows():
            # Split multiline strings
            time_parts = str(row['Time']).split('\n')
            team_parts = str(row['Teams']).split('\n')
            win_parts = str(row['Win']).replace('%', '').split('\n')
            
            # League specific point/goal column names
            score_col = 'Points' if league in ['nba', 'ncaab'] else 'Goals'
            score_parts = str(row[score_col]).split('\n')

            # Basic Fields
            raw_date = time_parts[0].strip() # MM/DD/YYYY
            try:
                formatted_date = datetime.strptime(raw_date, "%m/%d/%Y").strftime("%Y_%m_%DD")
            except:
                formatted_date = raw_date
                
            game_time = time_parts[1].strip() if len(time_parts) > 1 else ""
            
            # Team names (stripping records like (13-9))
            away_team = team_parts[0].split('(')[0].strip()
            home_team = team_parts[1].split('(')[0].strip() if len(team_parts) > 1 else ""
            
            # Probabilities
            p_away = float(win_parts[0])
            p_home = float(win_parts[1]) if len(win_parts) > 1 else 0.0
            
            # Points/Goals
            s_away = float(score_parts[0])
            s_home = float(score_parts[1]) if len(score_parts) > 1 else 0.0
            
            # Total
            if league in ['nba', 'ncaab']:
                total = row['Total\nPoints']
            else:
                total = s_away + s_home

            # Odds Logic
            fair_dec_away = 1 / (p_away / 100)
            fair_dec_home = 1 / (p_home / 100)
            acc_dec_away = fair_dec_away * 1.05
            acc_dec_home = fair_dec_home * 1.05

            entry = {
                "date": formatted_date,
                "time": game_time,
                "away_team": away_team,
                "home_team": home_team,
                "away_team_moneyline_win_prob": p_away,
                "home_team_moneyline_win_prob": p_home,
                f"away_team_projected_{score_col.lower()}": s_away,
                f"home_team_projected_{score_col.lower()}": s_home,
                f"game_projected_{score_col.lower()}": total,
                "league": league,
                "game_id": f"{league}_{formatted_date}_{index}",
                "fair_decimal_odds": round(fair_dec_away, 2),
                "fair_american_odds": conv_american(fair_dec_away),
                "acceptable_decimal_odds": round(acc_dec_away, 2),
                "acceptable_american_odds": conv_american(acc_dec_away)
            }
            processed_data.append(entry)

        # Create Output DF and Save
        out_df = pd.DataFrame(processed_data)
        out_filename = f"{league}_{formatted_date}.csv"
        out_df.to_csv(os.path.join(OUTPUT_DIR, out_filename), index=False)

if __name__ == "__main__":
    process_files()
