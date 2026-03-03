#!/usr/bin/env python3
# docs/win/hockey/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# Directory Configuration
INPUT_DIR = Path("docs/win/hockey/03_edges")
OUTPUT_DIR = Path("docs/win/hockey/04_select")
ERROR_DIR = Path("docs/win/hockey/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# Thresholds
TOTAL_MIN_EDGE_PCT = 0.03
TOTAL_MIN_PROB = 0.45

# Puck Line Specifics
PL_FAVORITE_EDGE_REQ = 0.05    # -1.5 lines
PL_UNDERDOG_EDGE_REQ = 0.02    # +1.5 lines
PL_MAX_FAVORITE_ODDS = -135    # Don't lay heavy juice on -1.5

LEAGUE_CODE = "NHL"
REQUIRED_GAME_COLS = ["game_date", "away_team", "home_team"]

def valid_edge(edge_pct, threshold):
    return pd.notna(edge_pct) and edge_pct >= threshold

def assert_required_cols(df: pd.DataFrame, df_name: str, log) -> bool:
    if df is None:
        return True
    missing = [c for c in REQUIRED_GAME_COLS if c not in df.columns]
    if missing:
        log.write(f"[COL ERROR] {df_name} missing: {missing}\n")
        return False
    return True

def build_matchups(df: pd.DataFrame) -> pd.DataFrame:
    return df[REQUIRED_GAME_COLS].dropna().drop_duplicates()

def main():
    with open(ERROR_LOG, "w") as log:
        log.write("=== NHL SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")
        log.write(f"Settings: PL Fav Edge {PL_FAVORITE_EDGE_REQ}, PL Dog Edge {PL_UNDERDOG_EDGE_REQ}\n\n")

        try:
            moneyline_files = sorted(INPUT_DIR.glob("*_NHL_moneyline.csv"))
            puckline_files = sorted(INPUT_DIR.glob("*_NHL_puck_line.csv"))
            total_files = sorted(INPUT_DIR.glob("*_NHL_total.csv"))

            all_files = moneyline_files + puckline_files + total_files
            slates = {}

            for f in all_files:
                slate_key = f.name.replace("_NHL_moneyline.csv", "").replace("_NHL_puck_line.csv", "").replace("_NHL_total.csv", "")
                slates.setdefault(slate_key, []).append(f)

            if not slates:
                log.write("No slates found to process.\n")
                return

            for slate_key in slates.keys():
                final_rows = []
                counts = {"moneyline": 0, "puck_line": 0, "total": 0}
                skipped_pl = 0

                ml_path = INPUT_DIR / f"{slate_key}_NHL_moneyline.csv"
                pl_path = INPUT_DIR / f"{slate_key}_NHL_puck_line.csv"
                total_path = INPUT_DIR / f"{slate_key}_NHL_total.csv"

                ml_df = pd.read_csv(ml_path) if ml_path.exists() else None
                pl_df = pd.read_csv(pl_path) if pl_path.exists() else None
                total_df = pd.read_csv(total_path) if total_path.exists() else None

                if not assert_required_cols(ml_df, "ML", log) or not assert_required_cols(pl_df, "PL", log) or not assert_required_cols(total_df, "Total", log):
                    log.write(f"Skipping slate {slate_key} | Column mismatch\n")
                    continue

                matchup_frames = [build_matchups(df) for df in [ml_df, pl_df, total_df] if df is not None and not df.empty]
                if not matchup_frames:
                    continue

                matchups = pd.concat(matchup_frames, ignore_index=True).drop_duplicates()

                for _, m in matchups.iterrows():
                    game_date, away, home = str(m["game_date"]), str(m["away_team"]), str(m["home_team"])

                    # 1. PUCK LINE LOGIC
                    if pl_df is not None:
                        game_pl = pl_df[(pl_df["game_date"].astype(str) == game_date) & (pl_df["away_team"] == away) & (pl_df["home_team"] == home)]
                        for _, row in game_pl.iterrows():
                            for side in ["home", "away"]:
                                line = pd.to_numeric(row.get(f"{side}_puck_line"), errors='coerce')
                                edge = pd.to_numeric(row.get(f"{side}_edge_pct"), errors='coerce')
                                odds = pd.to_numeric(row.get(f"{side}_dk_puck_line_american"), errors='coerce')
                                
                                if pd.isna(line) or pd.isna(edge): continue
                                
                                keep_pl = False
                                # Case A: Underdogs (+1.5)
                                if line > 0:
                                    if edge >= PL_UNDERDOG_EDGE_REQ:
                                        keep_pl = True
                                
                                # Case B: Favorites (-1.5)
                                elif line < 0:
                                    if edge >= PL_FAVORITE_EDGE_REQ and odds >= PL_MAX_FAVORITE_ODDS:
                                        keep_pl = True
                                
                                if keep_pl:
                                    final_rows.append({
                                        "game_date": game_date, "league": LEAGUE_CODE, "away_team": away, "home_team": home,
                                        "market_type": "puck_line", "bet_side": side, "line": line, "game_id": row.get("game_id"),
                                        "take_bet": f"{side}_puck_line", "take_bet_edge_pct": edge, "take_odds": odds
                                    })
                                    counts["puck_line"] += 1
                                else:
                                    skipped_pl += 1

                    # 2. MONEYLINE LOGIC
                    if ml_df is not None:
                        game_ml = ml_df[(ml_df["game_date"].astype(str) == game_date) & (ml_df["away_team"] == away) & (ml_df["home_team"] == home)]
                        best_ml_row, best_ml_edge = None, -float('inf')
                        for _, row in game_ml.iterrows():
                            for side in ["home", "away"]:
                                edge = pd.to_numeric(row.get(f"{side}_edge_pct"), errors='coerce')
                                prob = pd.to_numeric(row.get(f"{side}_prob"), errors='coerce')
                                odds = pd.to_numeric(row.get(f"{side}_dk_moneyline_american"), errors='coerce')
                                
                                if pd.isna(edge) or pd.isna(prob) or pd.isna(odds): continue

                                if (200 <= odds <= 225 and edge >= 0.05 and prob >= 0.35) or \
                                   (1 <= odds <= 199 and edge >= 0.05 and prob >= 0.38) or \
                                   (odds <= -100 and edge >= 0.04 and prob >= 0.55):
                                    if edge > best_ml_edge:
                                        best_ml_edge, best_ml_row = edge, (row, side, odds)
                        
                        if best_ml_row:
                            row, side, odds = best_ml_row
                            final_rows.append({
                                "game_date": game_date, "league": LEAGUE_CODE, "away_team": away, "home_team": home,
                                "market_type": "moneyline", "bet_side": side, "line": "", "game_id": row.get("game_id"),
                                "take_bet": f"{side}_moneyline", "take_bet_edge_pct": best_ml_edge, "take_odds": odds
                            })
                            counts["moneyline"] += 1

                    # 3. TOTAL LOGIC
                    if total_df is not None:
                        game_tot = total_df[(total_df["game_date"].astype(str) == game_date) & (total_df["away_team"] == away) & (total_df["home_team"] == home)]
                        best_tot_row, best_tot_edge = None, -float('inf')
                        for _, row in game_tot.iterrows():
                            for side in ["over", "under"]:
                                edge = pd.to_numeric(row.get(f"{side}_edge_pct"), errors='coerce')
                                prob = pd.to_numeric(row.get(f"juiced_total_{side}_prob"), errors='coerce')
                                if valid_edge(edge, TOTAL_MIN_EDGE_PCT) and prob >= TOTAL_MIN_PROB:
                                    if edge > best_tot_edge:
                                        best_tot_edge, best_tot_row = edge, (row, side)
                        
                        if best_tot_row:
                            row, side = best_tot_row
                            final_rows.append({
                                "game_date": game_date, "league": LEAGUE_CODE, "away_team": away, "home_team": home,
                                "market_type": "total", "bet_side": side, "line": row.get("total"), "game_id": row.get("game_id"),
                                "take_bet": f"total_{side}", "take_bet_edge_pct": best_tot_edge, "take_odds": row.get(f"dk_total_{side}_american")
                            })
                            counts["total"] += 1

                # Save Results
                out_df = pd.DataFrame(final_rows)
                if not out_df.empty:
                    out_df = out_df.drop_duplicates(subset=["game_date", "away_team", "home_team", "market_type", "bet_side", "line"])
                    out_df.to_csv(OUTPUT_DIR / f"{slate_key}_NHL_selections.csv", index=False)
                
                log.write(f"Processed Slate: {slate_key}\n")
                log.write(f"  - Moneyline: {counts['moneyline']} bets\n")
                log.write(f"  - Puck Line: {counts['puck_line']} bets (Skipped {skipped_pl})\n")
                log.write(f"  - Totals:    {counts['total']} bets\n\n")

        except Exception as e:
            log.write(f"\nCRITICAL ERROR: {str(e)}\n{traceback.format_exc()}\n")

if __name__ == "__main__":
    main()
