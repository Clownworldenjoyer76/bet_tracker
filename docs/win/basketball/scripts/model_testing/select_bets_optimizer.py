import pandas as pd
from pathlib import Path
import importlib.util

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_FILE = Path("docs/win/basketball/04_select/selected_bets.csv")
CONFIG_PATH = Path("docs/win/basketball/model_testing/rule_config.py")

def load_config():
    spec = importlib.util.spec_from_file_location("rule_config", CONFIG_PATH)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return cfg

def main():
    cfg = load_config()
    all_selected = []
    
    for csv_file in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(csv_file)
        league = "NBA" if "nba" in csv_file.name.lower() else "NCAAB"
        market = "total" if "total" in csv_file.name.lower() else "spread" if "spread" in csv_file.name.lower() else "ml"
        
        for _, row in df.iterrows():
            # Apply STD Filters
            std_val = row.get(f"{market}_std", 0)
            std_limit = getattr(cfg, f"{league}_{market.upper()}_STD", 99)
            if std_val > std_limit: continue
            
            # Apply Market Specific Rules
            edge = row["edge"]
            edge_min = getattr(cfg, f"{league}_{market.upper()}_EDGE_MIN", 0.05)
            if edge < edge_min or edge > cfg.EDGE_MAX: continue
            
            if market == "total" and row["total"] < cfg.TOTAL_MIN: continue
            if market == "spread" and abs(row["home_spread"]) > cfg.SPREAD_MAX: continue
            
            # Capture metadata for results tracking
            row["league"] = league
            row["market_type"] = market
            row["config_edge_min"] = edge_min
            all_selected.append(row)

    if all_selected:
        pd.DataFrame(all_selected).to_csv(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    main()
