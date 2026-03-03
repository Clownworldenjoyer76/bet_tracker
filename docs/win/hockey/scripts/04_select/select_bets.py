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

# Global Thresholds
TOTAL_MIN_EDGE_PCT = 0.05
TOTAL_MIN_PROB = 0.52

# Puck Line Specifics
PL_DOG_WIN_PROB_REQ = 0.63
PL_HUGE_FAV_EDGE = 0.15
PL_MAX_FAV_ODDS = -120

LEAGUE_CODE = "NHL"

def main():
    with open(ERROR_LOG, "w") as log:
        log.write("=== NHL SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:
            all_files = sorted(INPUT_DIR.glob("*_NHL_*.csv"))
            slates = {}

            for f in all_files:
                slate_key = f.name.split('_NHL_')[0]
                slates.setdefault(slate_key, []).append(f)

            if not slates:
                log.write("No input files found in docs/win/hockey/03_edges\n")
                return

            for slate_key in slates.keys():
                final_rows = []
                seen_bets = set()
                counts = {"moneyline": 0, "puck_line": 0, "total": 0}

                ml_path = INPUT_DIR / f"{slate_key}_NHL_moneyline.csv"
                pl_path = INPUT_DIR / f"{slate_key}_NHL_puck_line.csv"
                td_path = INPUT_DIR / f"{slate_key}_NHL_total.csv"

                ml_df = pd.read_csv(ml_path) if ml_path.exists() else None
                pl_df = pd.read_csv(pl_path) if pl_path.exists() else None
                td_df = pd.read_csv(td_path) if td_path.exists() else None

                if pl_df is None or pl_df.empty:
                    continue

                for _, row in pl_df.iterrows():
                    game_date = str(row.get("game_date"))
                    away = str(row.get("away_team"))
                    home = str(row.get("home_team"))
                    game_id = row.get("game_id")
                    selected_total_side = None

                    # --- TOTALS ---
                    if td_df is not None:
                        game_tot = td_df[(td_df["away_team"] == away) & (td_df["home_team"] == home)]
                        for _, trow in game_tot.iterrows():
                            for side in ["over", "under"]:
                                line = trow.get("total")
                                t_edge = pd.to_numeric(trow.get(f"{side}_edge_pct"), errors='coerce')
                                t_prob = pd.to_numeric(trow.get(f"juiced_total_{side}_prob"), errors='coerce')

                                if t_edge >= TOTAL_MIN_EDGE_PCT and t_prob >= TOTAL_MIN_PROB:
                                    bet_key = f"{game_date}_{away}_{home}_total_{side}_{line}"
                                    if bet_key not in seen_bets:
                                        selected_total_side = side
                                        final_rows.append({
                                            "game_date": game_date,
                                            "league": LEAGUE_CODE,
                                            "away_team": away,
                                            "home_team": home,
                                            "market_type": "total",
                                            "bet_side": side,
                                            "line": line,
                                            "game_id": game_id,
                                            "take_bet": f"{side}_total",
                                            "take_bet_edge_pct": t_edge,
                                            "take_odds": trow.get(f"dk_total_{side}_american")
                                        })
                                        seen_bets.add(bet_key)
                                        counts["total"] += 1

                    # --- PUCK LINE ---
                    for side in ["home", "away"]:
                        line = pd.to_numeric(row.get(f"{side}_puck_line"), errors='coerce')
                        edge = pd.to_numeric(row.get(f"{side}_edge_pct"), errors='coerce')
                        prob = pd.to_numeric(row.get(f"{side}_prob"), errors='coerce')
                        odds = pd.to_numeric(row.get(f"{side}_dk_puck_line_american"), errors='coerce')

                        if pd.isna(line):
                            continue

                        keep_pl = False

                        if line >= 1.5:
                            if prob >= PL_DOG_WIN_PROB_REQ:
                                keep_pl = True

                        elif line <= -1.5:
                            if selected_total_side == "under":
                                continue
                            if edge >= PL_HUGE_FAV_EDGE and odds >= PL_MAX_FAV_ODDS:
                                keep_pl = True

                        if keep_pl:
                            bet_key = f"{game_date}_{away}_{home}_puckline_{side}_{line}"
                            if bet_key not in seen_bets:
                                final_rows.append({
                                    "game_date": game_date,
                                    "league": LEAGUE_CODE,
                                    "away_team": away,
                                    "home_team": home,
                                    "market_type": "puck_line",
                                    "bet_side": side,
                                    "line": line,
                                    "game_id": game_id,
                                    "take_bet": f"{side}_puck_line",
                                    "take_bet_edge_pct": edge,
                                    "take_odds": odds
                                })
                                seen_bets.add(bet_key)
                                counts["puck_line"] += 1

                    # --- MONEYLINE ---
                    if ml_df is not None:
                        game_ml = ml_df[(ml_df["away_team"] == away) & (ml_df["home_team"] == home)]
                        for _, mrow in game_ml.iterrows():
                            for side in ["home", "away"]:
                                m_edge = pd.to_numeric(mrow.get(f"{side}_edge_pct"), errors='coerce')
                                m_prob = pd.to_numeric(mrow.get(f"{side}_prob"), errors='coerce')
                                m_odds = pd.to_numeric(mrow.get(f"{side}_dk_moneyline_american"), errors='coerce')

                                if m_edge >= 0.05 and m_prob >= 0.45:
                                    bet_key = f"{game_date}_{away}_{home}_moneyline_{side}"
                                    if bet_key not in seen_bets:
                                        final_rows.append({
                                            "game_date": game_date,
                                            "league": LEAGUE_CODE,
                                            "away_team": away,
                                            "home_team": home,
                                            "market_type": "moneyline",
                                            "bet_side": side,
                                            "line": "",
                                            "game_id": game_id,
                                            "take_bet": f"{side}_moneyline",
                                            "take_bet_edge_pct": m_edge,
                                            "take_odds": m_odds
                                        })
                                        seen_bets.add(bet_key)
                                        counts["moneyline"] += 1

                if final_rows:
                    out_df = pd.DataFrame(final_rows)

                    output_path = OUTPUT_DIR / f"{slate_key}_NHL.csv"
                    out_df.to_csv(output_path, index=False)

                    log.write(
                        f"Generated {output_path.name}: "
                        f"ML:{counts['moneyline']} "
                        f"PL:{counts['puck_line']} "
                        f"Tot:{counts['total']}\n"
                    )

        except Exception as e:
            log.write(f"CRITICAL ERROR: {str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
