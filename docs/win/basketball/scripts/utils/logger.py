import pandas as pd
import traceback
from datetime import datetime
from pathlib import Path

def audit(log_path, stage, status, msg="", df=None, condensed_path="condensed_betting_log.txt"):
    """
    Complete Logger: 
    1. Exhaustive version (full stats, nulls, samples).
    2. Condensed version (only high-value betting signals).
    """
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # --- 1. EXHAUSTIVE LOG (The Full Version) ---
    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: 
            f.write(f"  MSG: {msg}\n")
        
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  NULLS: {df.isnull().sum().sum()} total\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

    # --- 2. CONDENSED LOG (The Summary Version) ---
    # Only triggers if a DataFrame is passed and contains 'edge_pct'
    if df is not None and isinstance(df, pd.DataFrame) and 'edge_pct' in df.columns:
        # Filter for rows with a positive edge (profitable plays)
        signals = df[df['edge_pct'] > 0].sort_values(by='edge_pct', ascending=False)
        
        if not signals.empty:
            with open(condensed_path, "a") as cf:
                cf.write(f"--- BETTING SIGNALS: {ts} ---\n")
                # Adjust these column names if your headers are different
                cols = ['game_date', 'team', 'opponent', 'edge_pct']
                # Keep it strictly to the data, no extra fluff
                cf.write(signals[cols].to_string(index=False) + "\n")
                cf.write("-" * 30 + "\n")

# --- USAGE EXAMPLE ---
# audit("full_audit.log", "PREDICTION_STAGE", "SUCCESS", df=my_dataframe)
