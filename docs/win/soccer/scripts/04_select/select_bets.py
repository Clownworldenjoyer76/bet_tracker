#!/usr/bin/env python3

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================
INPUT_DIR = Path("docs/win/soccer/03_edges")
OUTPUT_DIR = Path("docs/win/soccer/04_select")
ERROR_DIR = Path("docs/win/soccer/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CRITERIA CONFIG
# =========================
MIN_EDGE_PCT = 0.03
DRAW_MIN_EDGE_PCT = 0.05
DRAW_MIN_PROB = 0.22
DRAW_DOMINANCE_MARGIN = 0.03
KELLY_FRACTION = 0.25  # 1/4 Kelly to manage bankroll

def parse_match_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p")
    except Exception:
        return None

def calculate_kelly(prob, odds, fraction=0.25):
    """Calculates suggested stake % using Fractional Kelly."""
    if odds <= 1 or prob <= 0: return 0
    f_star = (odds * prob - 1) / (odds - 1)
    return max(0, f_star * fraction)

def main():
    with open(ERROR_LOG, "a") as log:
        log.write(f"=== SELECT BETS RUN: {datetime.utcnow().isoformat()}Z ===\n")

        try:
            input_files = sorted(INPUT_DIR.glob("soccer_*.csv"))
            if not input_files:
                log.write("No input files found.\n")
                return

            for input_path in input_files:
                df = pd.read_csv(input_path)
                
                # Dynamic column check for all 7 markets
                core_markets = ["home", "draw", "away", "over25", "under25", "btts_yes", "btts_no"]
                selections = []

                for _, row in df.iterrows():
                    # 1. Build dictionary of all potential edges
                    all_edges = {}
                    for m in core_markets:
                        edge_col = f"{m}_edge_pct"
                        if edge_col in df.columns:
                            val = row[edge_col]
                            all_edges[m] = val if not pd.isna(val) else -999

                    # 2. Filter for MIN_EDGE_PCT
                    valid_edges = {k: v for k, v in all_edges.items() if v >= MIN_EDGE_PCT}
                    if not valid_edges:
                        continue

                    # 3. Find Best Side (Initial)
                    best_side = max(valid_edges, key=valid_edges.get)
                    best_edge = valid_edges[best_side]

                    # 4. Apply Special Draw Logic
                    if best_side == "draw":
                        sorted_edge_vals = sorted(all_edges.values(), reverse=True)
                        second_best_val = sorted_edge_vals[1] if len(sorted_edge_vals) > 1 else -999
                        
                        # Conditions to REJECT the draw as the primary pick
                        if (best_edge < DRAW_MIN_EDGE_PCT or 
                            row["draw_prob"] < DRAW_MIN_PROB or 
                            (best_edge - second_best_val) < DRAW_DOMINANCE_MARGIN):
                            
                            # Fallback to next best non-draw market if it meets MIN_EDGE_PCT
                            non_draw_valid = {k: v for k, v in valid_edges.items() if k != "draw"}
                            if non_draw_valid:
                                best_side = max(non_draw_valid, key=non_draw_valid.get)
                                best_edge = non_draw_valid[best_side]
                            else:
                                continue # Skip game if only a weak Draw was available

                    # 5. Calculate Kelly Stake
                    # Note: We use the DK Decimal and the Model Probability
                    odds = row[f"{best_side}_dk_decimal"]
                    prob = row[f"{best_side}_prob"] if f"{best_side}_prob" in row else row[f"{best_side}_win_prob"]
                    stake_pct = calculate_kelly(prob, odds, KELLY_FRACTION)

                    # 6. Build Selection Row
                    selections.append({
                        "league": row["league"],
                        "match_date": row["match_date"],
                        "match_time": row["match_time"],
                        "home_team": row["home_team"],
                        "away_team": row["away_team"],
                        "game_id": row["game_id"],
                        "take_bet": best_side,
                        "odds_american": row[f"{best_side}_american"],
                        "odds_decimal": odds,
                        "edge_pct": best_edge,
                        "kelly_stake_pct": round(stake_pct * 100, 2),
                        "expected_goals": row.get("expected_total_goals", "")
                    })

                if selections:
                    sel_df = pd.DataFrame(selections)
                    sel_df["_sort_time"] = sel_df["match_time"].apply(parse_match_time)
                    sel_df = sel_df.sort_values(by="_sort_time").drop(columns=["_sort_time"])
                    
                    output_path = OUTPUT_DIR / input_path.name
                    sel_df.to_csv(output_path, index=False)
                    log.write(f"Wrote {len(selections)} plays to {output_path}\n")

        except Exception as e:
            log.write(f"\nCRITICAL ERROR: {str(e)}\n{traceback.format_exc()}\n")

if __name__ == "__main__":
    main()
