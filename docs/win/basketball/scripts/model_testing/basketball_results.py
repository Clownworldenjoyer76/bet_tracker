import pandas as pd
from pathlib import Path

# ... [Keep your existing determine_outcome and safe_read_csv functions] ...

def generate_master_backtest_row(league, stats, config):
    """Creates the exact row format requested by the user."""
    row = {
        "RUN_DATE": pd.Timestamp.now().strftime("%Y_%m_%d"),
        "EDGE_MAX": config.get("EDGE_MAX"),
        "SPREAD_MAX": config.get("SPREAD_MAX"),
        "TOTAL_MIN": config.get("TOTAL_MIN"),
        # Add all your config variables here...
        f"{league}_SPREAD_WIN_PCT": stats.get("SPREAD_WIN_PCT"),
        f"{league}_SPREAD_BETS": stats.get("SPREAD_BETS"),
        f"{league}_TOTAL_WIN_PCT": stats.get("TOTAL_WIN_PCT"),
        # ... repeat for all stats keys ...
    }
    return row

def process_results():
    # 1. Grade the games
    # 2. Compute Stats
    # 3. Append to a Master CSV
    nba_stats = compute_stats(pd.read_csv(NBA_GRADED / "NBA_final.csv"))
    
    # Load config to include settings in the row
    from rule_config import EDGE_MAX, SPREAD_MAX # etc
    
    final_data = generate_master_backtest_row("NBA", nba_stats, locals())
    pd.DataFrame([final_data]).to_csv("backtest_results_master.csv", mode='a', index=False)

if __name__ == "__main__":
    process_results()
