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

    if df is not None and isinstance(df, pd.DataFrame) and 'edge_pct' in df.columns:
        condensed_path = log_path.parent / "condensed_report.csv"
        signals = df[df['edge_pct'] > 0].copy()
        
        if not signals.empty:
            signals['log_timestamp'] = ts
            cols = ['log_timestamp', 'game_date', 'team', 'opponent', 'edge_pct']
            signals[cols].to_csv(condensed_path, mode='a', index=False, header=not condensed_path.exists())
