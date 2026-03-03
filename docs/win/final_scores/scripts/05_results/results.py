import pandas as pd
import os
import glob
import re

def process_results():
    # Configuration for all sports
    configs = [
        {
            "name": "NHL",
            "scores_sub": "nhl",
            "bets_dir": "docs/win/hockey/04_select",
            "suffix": "NHL"
        },
        {
            "name": "NBA",
            "scores_sub": "nba",
            "bets_dir": "docs/win/basketball/04_select",
            "suffix": "NBA"
        },
        {
            "name": "NCAAB",
            "scores_sub": "ncaab",
            "bets_dir": "docs/win/basketball/04_select",
            "suffix": "NCAAB"
        }
    ]

    for cfg in configs:
        scores_dir = f"docs/win/final_scores/results/{cfg['scores_sub']}/final_scores"
        output_dir = f"docs/win/final_scores/results/{cfg['scores_sub']}/graded"
        os.makedirs(output_dir, exist_ok=True)

        # Find unique dates from bet files in the specific sport's bet directory
        search_pattern = os.path.join(cfg['bets_dir'], f"*_{cfg['suffix']}*.csv")
        bet_files = glob.glob(search_pattern)
        
        dates = set()
        for f in bet_files:
            match = re.search(r"(\d{4}_\d{2}_\d{2})", os.path.basename(f))
            if match:
                dates.add(match.group(1))

        for date_str in sorted(dates):
            score_file = os.path.join(scores_dir, f"{date_str}_final_scores_{cfg['suffix']}.csv")
            output_path = os.path.join(output_dir, f"{date_str}_results_{cfg['suffix']}.csv")

            if not os.path.exists(score_file):
                print(f"Skipping {cfg['name']} {date_str}: Score file not found.")
                continue

            # Find all market files for this date and sport (handles both hockey and basketball naming)
            daily_bet_files = glob.glob(os.path.join(cfg['bets_dir'], f"{date_str}_*_{cfg['suffix']}*.csv"))
            
            valid_dfs = []
            for bf in daily_bet_files:
                valid_dfs.append(pd.read_csv(bf))
            
            if not valid_dfs:
                continue

            bets_df = pd.concat(valid_dfs, ignore_index=True)
            scores_df = pd.read_csv(score_file)
            
            # Merge
            df = pd.merge(bets_df, scores_df, on=['away_team', 'home_team', 'game_date'], suffixes=('', '_scorefile'))

            def determine_outcome(row):
                m_type = str(row['market_type']).lower()
                side = str(row['bet_side']).lower()
                line = float(row['line'])
                away, home = float(row['away_score']), float(row['home_score'])
                total = away + home

                if m_type == 'total':
                    return 'Win' if (total < line if side == 'under' else total > line) else ('Push' if total == line else 'Loss')
                
                if m_type == 'moneyline':
                    return 'Win' if (away > home if side == 'away' else home > away) else 'Loss'
                
                # Handles both 'spread' (NBA) and 'puck_line' (NHL)
                if m_type in ['spread', 'puck_line']:
                    diff = (away + line) - home if side == 'away' else (home + line) - away
                    return 'Win' if diff > 0 else ('Push' if diff == 0 else 'Loss')
                
                return 'Unknown'

            df['bet_result'] = df.apply(determine_outcome, axis=1)
            
            # Save output
            output_cols = ['game_date', 'away_team', 'home_team', 'market_type', 'bet_side', 'line', 'away_score', 'home_score', 'bet_result']
            df[output_cols].to_csv(output_path, index=False)
            print(f"Processed {cfg['name']}: {date_str} -> {output_path}")

if __name__ == "__main__":
    process_results()
