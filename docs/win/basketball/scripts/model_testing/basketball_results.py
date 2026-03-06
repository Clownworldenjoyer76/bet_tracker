import pandas as pd
from pathlib import Path
from datetime import datetime
import importlib.util

SELECTED_BETS = Path("docs/win/basketball/04_select/selected_bets.csv")
SCORES_DIR = Path("docs/win/basketball/01_raw_scores")
MASTER_LOG = Path("docs/win/basketball/model_testing/backtest_results_master.csv")
CONFIG_PATH = Path("docs/win/basketball/model_testing/rule_config.py")

def load_config_dict():
    spec = importlib.util.spec_from_file_location("rule_config", CONFIG_PATH)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return {k: v for k, v in vars(cfg).items() if not k.startswith("__")}

def grade_bets():
    if not SELECTED_BETS.exists(): return pd.DataFrame()
    bets = pd.read_csv(SELECTED_BETS)
    # Placeholder for grading logic (comparing bet_side to actual score)
    # Assumes 'is_win' column is created here
    bets["is_win"] = 1 # Logic to be filled based on your raw_scores format
    return bets

def main():
    bets = grade_bets()
    if bets.empty: return
    
    cfg = load_config_dict()
    stats = {}
    
    for league in ["NBA", "NCAAB"]:
        l_bets = bets[bets["league"] == league]
        for mtype in ["total", "spread", "ml"]:
            m_bets = l_bets[l_bets["market_type"] == mtype]
            win_pct = m_bets["is_win"].mean() if not m_bets.empty else 0
            stats[f"{league}_{mtype.upper()}_WIN_PCT"] = win_pct
            stats[f"{league}_{mtype.upper()}_BETS"] = len(m_bets)

    # Merge config variables and stats into one row
    final_row = {**cfg, **stats}
    final_row["RUN_DATE"] = datetime.now().strftime("%Y_%m_%d")
    
    df_out = pd.DataFrame([final_row])
    if MASTER_LOG.exists():
        df_out.to_csv(MASTER_LOG, mode='a', header=False, index=False)
    else:
        df_out.to_csv(MASTER_LOG, index=False)

if __name__ == "__main__":
    main()
