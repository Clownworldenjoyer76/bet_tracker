import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_FILE = Path("docs/win/basketball/04_select/selected_bets.csv")
STATS_FILE = Path("docs/win/basketball/model_testing/optimizer_stats.csv")
CONFIG_PATH = Path("docs/win/basketball/model_testing/rule_config.py")

def load_config():
    cfg = {
        "EDGE_MAX": 0.30, "SPREAD_MAX": 20, "TOTAL_MIN": 140,
        "NBA_TOTAL_STD_MAX": 15, "NBA_SPREAD_STD_MAX": 15, # Added STD
        "NBA_TOTAL_EDGE_MIN": 0.00, "NCAAB_TOTAL_EDGE_MIN": 0.00,
        "NBA_SPREAD_EDGE_MIN": 0.00, "NCAAB_SPREAD_EDGE_MIN": 0.00,
        "NBA_ML_HOME_EDGE_MIN": 0.00, "NBA_ML_AWAY_EDGE_MIN": 0.00,
        "NBA_ML_HOME_ODDS_MIN": -10000, "NBA_ML_HOME_ODDS_MAX": 10000,
        "NBA_ML_AWAY_ODDS_MIN": -10000, "NBA_ML_AWAY_ODDS_MAX": 10000,
    }
    if CONFIG_PATH.exists():
        scope = {}
        exec(CONFIG_PATH.read_text(), {}, scope)
        cfg.update({k: v for k, v in scope.items() if k in cfg})
    return cfg

CFG = load_config()

def f(x):
    try: return float(x)
    except: return 0.0

def main():
    all_candidates = []
    for csv_file in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(csv_file)
        league = "NBA" if "nba" in csv_file.name.lower() else "NCAAB"
        
        for _, row in df.iterrows():
            m_type = "total" if "total" in csv_file.name.lower() else "spread" if "spread" in csv_file.name.lower() else "moneyline"
            
            # STD FILTER (New)
            std = f(row.get(f"{m_type}_std", 0))
            if std > CFG.get(f"{league}_{m_type.upper()}_STD_MAX", 99): continue

            # EXISTING FILTERS (Edge, Odds, Rules)
            # ... [Existing logic for market-specific filtering goes here] ...
            
            new_row = row.copy()
            new_row["market_type"] = m_type
            new_row["candidate_edge"] = f(row.get("edge")) # Standardized
            all_candidates.append(new_row)

    df_final = pd.DataFrame(all_candidates)
    df_final.to_csv(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    main()
