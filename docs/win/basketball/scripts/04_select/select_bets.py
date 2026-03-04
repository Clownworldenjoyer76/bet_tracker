#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from datetime import datetime

# =========================
# EDGE THRESHOLDS
# =========================
SPREAD_THRESHOLD = 0.10
TOTAL_THRESHOLD = 0.16
ML_THRESHOLD = 0.07

# =========================
# LOGGER UTILITY
# =========================
def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg: f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")

    if df is not None and isinstance(df, pd.DataFrame):
        summary_path = log_path.parent / "condensed_summary.txt"
        if 'bet_side' in df.columns:
            with open(summary_path, "a") as f:
                f.write(f"\n--- BET SELECTIONS: {ts} ---\n")
                cols = ['game_date', 'home_team', 'away_team', 'market_type', 'bet_side', 'line']
                final_cols = [c for c in cols if c in df.columns]
                f.write(df[final_cols].to_string(index=False))
                f.write("\n" + "="*30 + "\n")

# =========================
# PATHS
# =========================
INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "select_bets_audit.txt"

def main():
    for csv_file in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(csv_file)
        fname = csv_file.name.lower()
        results = []

        for _, row in df.iterrows():
            # 1. ALWAYS CHOOSE STRONGEST SIDE
            if "total" in fname:
                edges = {"over": float(row.get("over_edge_decimal", 0)), 
                         "under": float(row.get("under_edge_decimal", 0))}
                m_type = "total"
            else:
                edges = {"home": float(row.get("home_edge_decimal", 0)), 
                         "away": float(row.get("away_edge_decimal", 0))}
                m_type = "spread" if "spread" in fname else "moneyline"

            side = max(edges, key=edges.get)
            edge = edges[side]
            
            # Extract common variables
            line = float(row.get("total" if m_type == "total" else f"{side}_spread", 0))
            odds = float(row.get(f"{side}_juice_odds", 0))
            fav_ud = "favorite" if odds < 0 else "underdog"
            venue = side

            # 2. APPLY MARKET FILTERS
            if m_type == "total":
                if line > 245: continue
                edge_req = TOTAL_THRESHOLD
                if line <= 205:
                    if side == "over": edge_req -= 0.04
                    if side == "under": continue
                
                if edge >= edge_req:
                    new_row = row.copy()
                    new_row.update({"market_type": "total", "bet_side": side, "line": line})
                    results.append(new_row)

            elif m_type == "spread":
                if abs(line) > 15: continue
                if line <= -7.5 and venue == "home": continue
                
                if edge >= SPREAD_THRESHOLD and abs(line) <= 10.5:
                    new_row = row.copy()
                    new_row.update({"market_type": "spread", "bet_side": side, "line": line})
                    results.append(new_row)

            elif m_type == "moneyline":
                if fav_ud == "favorite" and odds <= -500: continue
                if fav_ud == "underdog" and odds >= 350: continue
                if fav_ud == "favorite" and venue == "home" and -180 <= odds <= -150: continue

                edge_req = 0.08 if fav_ud == "favorite" else 0.07
                if fav_ud == "underdog" and venue == "away" and 130 <= odds <= 170:
                    edge_req = 0.06
                if venue == "home":
                    edge_req += 0.02
                
                if edge >= edge_req:
                    new_row = row.copy()
                    new_row.update({"market_type": "moneyline", "bet_side": side, "line": odds})
                    results.append(new_row)

        if results:
            res_df = pd.DataFrame(results).drop_duplicates()
            res_df.to_csv(OUTPUT_DIR / csv_file.name, index=False)
            audit(LOG_FILE, "SELECTION", "SUCCESS", msg=f"Selected {len(res_df)} from {csv_file.name}", df=res_df)
        else:
            audit(LOG_FILE, "SELECTION", "INFO", msg=f"No bets for {csv_file.name}")

if __name__ == "__main__":
    main()
