# docs/win/final_scores/scripts/utils/logger.py

import pandas as pd
from datetime import datetime
from pathlib import Path

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. EXHAUSTIVE LOG (The "Everything" file)
    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        f.write("-" * 40 + "\n")

    # 2. SEPARATE MARKET SUMMARIES (The "Clean" files)
    if df is not None and isinstance(df, pd.DataFrame):
        # Creates a file name based on the stage (e.g., "NBA_summary.txt")
        clean_stage_name = stage.replace(" ", "_").upper()
        summary_path = log_path.parent / f"{clean_stage_name}_summary.txt"

        play_cols = [c for c in ['home_play', 'away_play', 'over_play', 'under_play'] if c in df.columns]

        if play_cols:
            signals = df[df[play_cols].any(axis=1)].copy()

            if not signals.empty:
                # "w" ensures this specific market file is fresh every run
                with open(summary_path, "w") as f:
                    f.write(f"--- {clean_stage_name} SIGNALS: {ts} ---\n")

                    base_cols = ['game_date', 'home_team', 'away_team']
                    edge_cols = [c for c in df.columns if 'edge_pct' in c]
                    final_cols = [c for c in base_cols + edge_cols if c in signals.columns]

                    # Remove duplicates within this specific run
                    clean_df = signals[final_cols].drop_duplicates()

                    f.write(clean_df.to_string(index=False))
                    f.write("\n" + "=" * 30 + "\n")
