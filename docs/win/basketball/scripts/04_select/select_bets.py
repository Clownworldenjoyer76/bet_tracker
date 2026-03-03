#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# Directory Configuration
INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# Global Constants
MIN_TOTAL_ODDS = -150
REQUIRED_GAME_COLS = ["game_date", "away_team", "home_team"]

def infer_market_from_filename(filename: str):
    name = filename.lower()
    if "moneyline" in name: return "moneyline"
    if "spread" in name: return "spread"
    if "total" in name: return "total"
    return None

def infer_league(row_league, filename: str) -> str:
    rl = "" if pd.isna(row_league) else str(row_league).strip().upper()
    fn = filename.lower()
    if rl in {"NBA", "NCAAB"}: return rl
    if "ncaab" in fn or "college" in fn: return "NCAAB"
    if "nba" in fn: return "NBA"
    return "UNKNOWN"

def main():
    with open(ERROR_LOG, "w") as log:
        log.write("=== BASKETBALL SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:
            input_files = sorted(INPUT_DIR.glob("*.csv"))
            if not input_files:
                log.write("No input files found.\n")
                return

            for input_path in input_files:
                df = pd.read_csv(input_path)
                market = infer_market_from_filename(input_path.name)
                
                if market is None:
                    log.write(f"Skipping {input_path.name} (unknown market)\n")
                    continue

                selections = []
                counts = {"processed": 0, "selected": 0, "skipped": 0}

                for _, row in df.iterrows():
                    counts["processed"] += 1
                    league = infer_league(row.get("league"), input_path.name)
                    game_date = str(row.get("game_date", ""))
                    away = str(row.get("away_team", ""))
                    home = str(row.get("home_team", ""))
                    
                    keep_bet = False
                    side = None
                    line_val = ""
                    total_val = ""

                    # =========================
                    # MONEYLINE LOGIC
                    # =========================
                    if market == "moneyline":
                        for s in ["home", "away"]:
                            edge_dec = row.get(f"{s}_edge_decimal")
                            edge_pct = row.get(f"{s}_edge_pct")
                            win_prob = row.get(f"{s}_prob")
                            odds = pd.to_numeric(row.get(f"{s}_juice_odds"), errors="coerce")

                            if pd.isna(edge_dec) or pd.isna(win_prob) or pd.isna(odds): continue

                            if league == "NBA":
                                if odds >= 300: continue
                                elif 100 <= odds <= 149 and edge_dec >= 0.05 and win_prob >= 0.42: keep_bet, side = True, s
                                elif 150 <= odds <= 199 and edge_dec >= 0.06 and win_prob >= 0.40: keep_bet, side = True, s
                                elif 200 <= odds <= 299 and edge_dec >= 0.07 and win_prob >= 0.35: keep_bet, side = True, s
                                elif -149 <= odds <= -100 and edge_dec >= 0.05 and win_prob >= 0.58: keep_bet, side = True, s
                                elif -249 <= odds <= -150 and edge_dec >= 0.06 and win_prob >= 0.62: keep_bet, side = True, s
                                elif odds <= -250 and edge_dec >= 0.08 and win_prob >= 0.80: keep_bet, side = True, s

                            elif league == "NCAAB":
                                if s == "away" and win_prob < 0.65: continue
                                if odds >= 300 or win_prob < 0.30: continue
                                elif 200 <= odds < 300 and edge_dec >= 0.08 and edge_pct >= 0.035: keep_bet, side = True, s
                                elif 100 <= odds < 200 and edge_dec >= 0.06 and edge_pct >= 0.03: keep_bet, side = True, s
                                elif -200 <= odds < -100 and edge_dec >= 0.06 and edge_pct >= 0.03 and win_prob >= 0.60: keep_bet, side = True, s
                                elif odds < -200 and edge_dec >= 0.07 and edge_pct >= 0.03 and win_prob >= 0.72: keep_bet, side = True, s
                            if keep_bet: break

                    # =========================
                    # SPREAD LOGIC
                    # =========================
                    elif market == "spread":
                        for s in ["home", "away"]:
                            edge_dec = row.get(f"{s}_edge_decimal")
                            edge_pct = row.get(f"{s}_edge_pct")
                            line_val = row.get(f"{s}_spread")

                            if pd.isna(edge_dec) or pd.isna(line_val): continue
                            
                            if league == "NBA":
                                if abs(float(line_val)) > 10.5: continue
                                if edge_dec >= 0.06 and edge_pct >= 0.03: keep_bet, side = True, s

                            elif league == "NCAAB":
                                if abs(float(line_val)) > 12.5: continue
                                if edge_dec >= 0.07 and edge_pct >= 0.03: keep_bet, side = True, s
                            if keep_bet: break

                    # =========================
                    # TOTAL LOGIC
                    # =========================
                    elif market == "total":
                        for s in ["over", "under"]:
                            edge_dec = row.get(f"{s}_edge_decimal")
                            edge_pct = row.get(f"{s}_edge_pct")
                            total_val = pd.to_numeric(row.get("total"), errors="coerce")
                            odds = pd.to_numeric(row.get(f"total_{s}_juice_odds"), errors="coerce")

                            if pd.isna(odds) or pd.isna(total_val) or odds < MIN_TOTAL_ODDS: continue

                            if league == "NBA":
                                if edge_dec >= 0.12: keep_bet, side = True, s
                                
                            elif league == "NCAAB":
                                # Reverted range filter, relaxed edge for NCAAB
                                if edge_dec >= 0.08 and edge_pct >= 0.04: keep_bet, side = True, s
                            if keep_bet: break

                    if keep_bet:
                        take_odds = row.get(f"{side}_juice_odds") if market == "moneyline" else \
                                    row.get(f"{side}_spread_juice_odds") if market == "spread" else \
                                    row.get(f"total_{side}_juice_odds")
                        
                        selections.append({
                            "game_date": game_date, "league": league, "away_team": away, "home_team": home,
                            "market_type": market, "bet_side": side, "line": line_val if market == "spread" else total_val if market == "total" else "",
                            "game_id": row.get("game_id"), "take_odds": take_odds, "take_team": side,
                            "take_bet_edge_decimal": edge_dec, "take_bet_edge_pct": edge_pct
                        })
                        counts["selected"] += 1

                if selections:
                    out_df = pd.DataFrame(selections)
                    out_df.to_csv(OUTPUT_DIR / input_path.name, index=False)
                
                log.write(f"Processed: {input_path.name}\n")
                log.write(f"  - Total Rows: {counts['processed']} | Selected: {counts['selected']}\n\n")

        except Exception as e:
            log.write(f"CRITICAL ERROR: {str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
