# docs/win/basketball/scripts/utils/logger.py

import pandas as pd
from datetime import datetime
from pathlib import Path

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. EXHAUSTIVE LOG (TXT) - Keep as append so you have history
    log_mode = "a" 

    with open(log_path, log_mode) as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg:
            f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

    # 2. CONDENSED SUMMARY (TXT) - Overwrite so no dupes
    if df is not None and isinstance(df, pd.DataFrame):
        summary_path = log_path.parent / "condensed_summary.txt"

        play_cols = [c for c in ['home_play', 'away_play', 'over_play', 'under_play'] if c in df.columns]

        if play_cols:
            signals = df[df[play_cols].any(axis=1)].copy()

            if not signals.empty:
                # FIX: Use "w" to overwrite old signals with fresh ones
                summary_mode = "w" 

                with open(summary_path, summary_mode) as f:
                    f.write(f"--- LATEST BETTING SIGNALS: {ts} ---\n")

                    base_cols = ['game_date', 'home_team', 'away_team']
                    edge_cols = [c for c in df.columns if 'edge_pct' in c]
                    final_cols = [c for c in base_cols + edge_cols if c in signals.columns]

                    # Drop duplicates in the dataframe itself just in case
                    clean_signals = signals[final_cols].drop_duplicates()

                    f.write(clean_signals.to_string(index=False))
                    f.write("\n" + "=" * 30 + "\n")
