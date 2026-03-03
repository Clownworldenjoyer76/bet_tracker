import pandas as pd
import os
import glob
import re
from pathlib import Path
import traceback

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

            # 🔥 FIXED GLOB — now matches 2026_02_25_NHL.csv AND basketball-style names
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
                'bet_result'
            ]

            df[output_cols].to_csv(output_path, index=False)
            print(f"Processed {cfg['name']}: {date_str} -> {output_path}")


if __name__ == "__main__":
    process_results()
