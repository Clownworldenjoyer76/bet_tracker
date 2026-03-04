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
    
    # 1. EXHAUSTIVE LOG (TXT)
    log_mode = "w" if not log_path.exists() else "a"
    with open(log_path, log_mode) as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

    # 2. CONDENSED SUMMARY (TXT)
    if df is not None and isinstance(df, pd.DataFrame):
        summary_path = log_path.parent / "condensed_summary.txt"
        play_cols = [c for c in ['home_play', 'away_play', 'over_play', 'under_play'] if c in df.columns]
        if play_cols:
            signals = df[df[play_cols].any(axis=1)].copy()
            if not signals.empty:
                summary_mode = "w" if not summary_path.exists() else "a"
                with open(summary_path, summary_mode) as f:
                    f.write(f"\n--- BETTING SIGNALS: {ts} ---\n")
                    base_cols = ['game_date', 'home_team', 'away_team']
                    edge_cols = [c for c in df.columns if 'edge_pct' in c]
                    final_cols = [c for c in base_cols + edge_cols if c in signals.columns]
                    f.write(signals[final_cols].to_string(index=False))
                    f.write("\n" + "=" * 30 + "\n")

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
    # Reset error log each run
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== Results Script Log ===\n\n")

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

        search_pattern = os.path.join(cfg['bets_dir'], f"*{cfg['suffix']}*.csv")
        bet_files = glob.glob(search_pattern)

        dates = set()
        for f in bet_files:
            match = re.search(r"(\d{4}_\d{2}_\d{2})", os.path.basename(f))
            if match:
                dates.add(match.group(1))

        for date_str in sorted(dates):
            score_file = os.path.join(
                scores_dir,
                f"{date_str}_final_scores_{cfg['suffix']}.csv"
            )
            output_path = os.path.join(
                output_dir,
                f"{date_str}_results_{cfg['suffix']}.csv"
            )

            if not os.path.exists(score_file):
                print(f"Skipping {cfg['name']} {date_str}: Score file not found.")
                continue

            # Fixed glob
            daily_bet_files = glob.glob(
                os.path.join(cfg['bets_dir'], f"{date_str}*{cfg['suffix']}*.csv")
            )

            valid_dfs = []

            for bf in daily_bet_files:
                try:
                    df_temp = pd.read_csv(bf)

                    if df_temp.empty:
                        msg = f"EMPTY BET FILE: {bf}"
                        print(msg)
                        log_error(msg)
                        continue

                    valid_dfs.append(df_temp)

                except pd.errors.EmptyDataError:
                    msg = f"EMPTY BET FILE (no columns): {bf}"
                    print(msg)
                    log_error(msg)
                    continue

                except Exception:
                    msg = f"ERROR READING FILE: {bf}\n{traceback.format_exc()}"
                    print(msg)
                    log_error(msg)
                    continue

            if not valid_dfs:
                msg = f"No valid bet data for {cfg['name']} {date_str}"
                print(msg)
                log_error(msg)
                continue

            bets_df = pd.concat(valid_dfs, ignore_index=True)
            scores_df = pd.read_csv(score_file)

            df = pd.merge(
                bets_df,
                scores_df,
                on=['away_team', 'home_team', 'game_date'],
                suffixes=('', '_scorefile')
            )

            if df.empty:
                msg = f"No merged matches for {cfg['name']} {date_str}"
                print(msg)
                log_error(msg)
                continue

            def determine_outcome(row):
                m_type = str(row['market_type']).lower()
                side = str(row['bet_side']).lower()
                line = float(row['line'])
                away, home = float(row['away_score']), float(row['home_score'])
                total = away + home

                if m_type == 'total':
                    if total == line:
                        return 'Push'
                    return 'Win' if (total < line if side == 'under' else total > line) else 'Loss'

                if m_type == 'moneyline':
                    return 'Win' if (away > home if side == 'away' else home > away) else 'Loss'

                if m_type in ['spread', 'puck_line']:
                    diff = (away + line) - home if side == 'away' else (home + line) - away
                    if diff == 0:
                        return 'Push'
                    return 'Win' if diff > 0 else 'Loss'

                return 'Unknown'

            df['bet_result'] = df.apply(determine_outcome, axis=1)

            output_cols = [
                'game_date',
                'away_team',
                'home_team',
                'market_type',
                'bet_side',
                'line',
                'away_score',
                'home_score',
                'bet_result',
                'home_edge_decimal',
                'away_edge_decimal',
                'over_edge_decimal',
                'under_edge_decimal'
            ]

            # FIX: prevent KeyError if certain edge columns do not exist
            existing_cols = [c for c in output_cols if c in df.columns]
            df = df[existing_cols]

            df.to_csv(output_path, index=False)
            audit(ERROR_LOG, "GRADING", "SUCCESS", msg=f"Graded {cfg['name']} {date_str}", df=df)

            print(f"Processed {cfg['name']}: {date_str} -> {output_path}")


if __name__ == "__main__":
    process_results()
