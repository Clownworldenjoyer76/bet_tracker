# docs/win/final_scores/scripts/05_results/results.py
import pandas as pd
import os
import glob
import re
from pathlib import Path
import traceback
from datetime import datetime
import sys

# =========================
# LOGGER UTILITY
# =========================

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    log_mode = "w" if not log_path.exists() else "a"
    with open(log_path, log_mode) as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

# =========================
# ORIGINAL SCRIPT
# =========================

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG = ERROR_DIR / "results_errors.txt"

def log_error(message):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def process_results():
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== Results Script Log ===\n\n")

    configs = [
        {"name": "NHL", "scores_sub": "nhl", "bets_dir": "docs/win/hockey/04_select", "suffix": "NHL"},
        {"name": "NBA", "scores_sub": "nba", "bets_dir": "docs/win/basketball/04_select", "suffix": "NBA"},
        {"name": "NCAAB", "scores_sub": "ncaab", "bets_dir": "docs/win/basketball/04_select", "suffix": "NCAAB"}
    ]

    for cfg in configs:
        scores_dir = f"docs/win/final_scores/results/{cfg['scores_sub']}/final_scores"
        output_dir = f"docs/win/final_scores/results/{cfg['scores_sub']}/graded"
        os.makedirs(output_dir, exist_ok=True)

        search_pattern = os.path.join(cfg['bets_dir'], f"*{cfg['suffix']}*.csv")
        bet_files = glob.glob(search_pattern)

        dates = set()
        for f in bet_files:
            match = re.search(r"(\d{4}_\d{2}_\d{2})", os.path.basename(f))
            if match: dates.add(match.group(1))

        for date_str in sorted(dates):
            score_file = os.path.join(scores_dir, f"{date_str}_final_scores_{cfg['suffix']}.csv")
            output_path = os.path.join(output_dir, f"{date_str}_results_{cfg['suffix']}.csv")

            if not os.path.exists(score_file):
                print(f"Skipping {cfg['name']} {date_str}: Score file not found.")
                continue

            daily_bet_files = glob.glob(os.path.join(cfg['bets_dir'], f"{date_str}*{cfg['suffix']}*.csv"))
            valid_dfs = []

            for bf in daily_bet_files:
                try:
                    df_temp = pd.read_csv(bf)
                    if df_temp.empty: continue
                    valid_dfs.append(df_temp)
                except Exception:
                    log_error(f"ERROR READING FILE: {bf}\n{traceback.format_exc()}")
                    continue

            if not valid_dfs: continue

            bets_df = pd.concat(valid_dfs, ignore_index=True)
            scores_df = pd.read_csv(score_file)

            df = pd.merge(bets_df, scores_df, on=['away_team', 'home_team', 'game_date'], suffixes=('', '_scorefile'))
            if df.empty: continue

            def determine_outcome(row):
                # Identification logic using provided headers
                m_type, side, line = 'unknown', 'unknown', 0.0

                # Check Totals (NBA/NCAAB)
                if 'over_play' in row or 'under_play' in row:
                    m_type = 'total'
                    line = float(row.get('total', 0))
                    side = 'over' if str(row.get('over_play')).lower() == 'true' else 'under'
                
                # Check Spreads (NBA/NCAAB)
                elif 'home_spread' in row or 'away_spread' in row:
                    m_type = 'spread'
                    if str(row.get('home_play')).lower() == 'true':
                        side, line = 'home', float(row.get('home_spread', 0))
                    else:
                        side, line = 'away', float(row.get('away_spread', 0))

                # Check Moneyline (NBA/NCAAB)
                elif 'home_play' in row or 'away_play' in row:
                    m_type = 'moneyline'
                    side = 'home' if str(row.get('home_play')).lower() == 'true' else 'away'
                
                # Check NHL (uses market_type)
                elif 'market_type' in row:
                    m_type, side, line = str(row['market_type']).lower(), str(row['bet_side']).lower(), float(row['line'])

                away_s, home_s = float(row['away_score']), float(row['home_score'])
                
                if m_type == 'total':
                    res = away_s + home_s
                    if res == line: return 'Push'
                    return 'Win' if (res < line if side == 'under' else res > line) else 'Loss'
                if m_type == 'moneyline':
                    return 'Win' if (away_s > home_s if side == 'away' else home_s > away_s) else 'Loss'
                if m_type in ['spread', 'puck_line']:
                    diff = (away_s + line) - home_s if side == 'away' else (home_s + line) - away_s
                    if diff == 0: return 'Push'
                    return 'Win' if diff > 0 else 'Loss'
                return 'Unknown'

            df['bet_result'] = df.apply(determine_outcome, axis=1)

            # Use headers that actually exist in the merged dataframe
            output_cols = ['game_date', 'away_team', 'home_team', 'away_score', 'home_score', 'bet_result']
            optional = ['market', 'market_type', 'bet_side', 'line', 'home_edge_decimal', 'away_edge_decimal', 'over_edge_decimal', 'under_edge_decimal']
            existing = output_cols + [c for c in optional if c in df.columns]
            
            df[existing].to_csv(output_path, index=False)
            audit(ERROR_LOG, "GRADING", "SUCCESS", msg=f"Graded {cfg['name']} {date_str}", df=df)

if __name__ == "__main__":
    process_results()
