import pandas as pd
from datetime import datetime
from pathlib import Path

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

    if df is not None and isinstance(df, pd.DataFrame):
        condensed_path = log_path.parent / "condensed_report.csv"
        
        # Identify play columns based on your headers
        play_cols = [c for c in ['home_play', 'away_play', 'over_play', 'under_play'] if c in df.columns]
        
        if play_cols:
            # Filter rows where any play column is True
            signals = df[df[play_cols].any(axis=1)].copy()
            
            if not signals.empty:
                signals['log_timestamp'] = ts
                # Core identifiers + relevant edge/play columns
                cols_to_keep = ['log_timestamp', 'game_date', 'home_team', 'away_team', 'market']
                cols_to_keep += [c for c in df.columns if 'edge_pct' in c or 'play' in c]
                
                # Filter to only columns that actually exist in the current dataframe
                final_cols = [c for c in cols_to_keep if c in signals.columns]
                
                signals[final_cols].to_csv(condensed_path, mode='a', index=False, header=not condensed_path.exists())
