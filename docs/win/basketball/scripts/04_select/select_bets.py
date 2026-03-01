#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

MIN_EDGE_DECIMAL = 0.05
MIN_EDGE_PCT = 0.02

MIN_TOTAL_EDGE_DECIMAL = 0.12
MIN_TOTAL_EDGE_PCT = 0.06

# Totals odds gate (-150 or better)
MIN_TOTAL_ODDS = -150


def valid_edge(edge_dec, edge_pct):
    return (
        pd.notna(edge_dec)
        and pd.notna(edge_pct)
        and edge_dec >= MIN_EDGE_DECIMAL
        and edge_pct >= MIN_EDGE_PCT
    )


def valid_total_edge(edge_dec, edge_pct):
    return (
        pd.notna(edge_dec)
        and pd.notna(edge_pct)
        and edge_dec >= MIN_TOTAL_EDGE_DECIMAL
        and edge_pct >= MIN_TOTAL_EDGE_PCT
    )


def valid_total_odds(odds):
    odds_num = pd.to_numeric(odds, errors="coerce")
    return pd.notna(odds_num) and odds_num >= MIN_TOTAL_ODDS


def infer_market_from_filename(filename: str):
    name = filename.lower()
    if "moneyline" in name:
        return "moneyline"
    if "spread" in name:
        return "spread"
    if "total" in name:
        return "total"
    return None


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
                selections = []

                market = infer_market_from_filename(input_path.name)
                if market is None:
                    log.write(f"Skipping {input_path.name} (cannot infer market)\n")
                    continue

                for _, row in df.iterrows():

                    game_id = row.get("game_id")
                    league = row.get("league")

                    # =========================
                    # MONEYLINE
                    # =========================

                    if market == "moneyline":

                        for side in ["home", "away"]:

                            edge_dec = row.get(f"{side}_edge_decimal")
                            edge_pct = row.get(f"{side}_edge_pct")
                            win_prob = row.get(f"{side}_prob")
                            american_odds = row.get(f"{side}_juice_odds")

                            if pd.isna(edge_dec) or pd.isna(edge_pct) or pd.isna(win_prob):
                                continue

                            # ---- APPLY NBA FILTER ONLY ----
                            if str(league).upper() == "NBA":

                                odds = pd.to_numeric(american_odds, errors="coerce")
                                if pd.isna(odds):
                                    continue

                                # 🟢 Small Dogs (+100 to +149)
                                if 100 <= odds <= 149:
                                    if not (edge_dec >= 0.05 and win_prob >= 0.42):
                                        continue

                                # 🟢 Mid Dogs (+150 to +199)
                                elif 150 <= odds <= 199:
                                    if not (edge_dec >= 0.06 and win_prob >= 0.38):
                                        continue

                                # 🟡 Large Dogs (+200 to +299)
                                elif 200 <= odds <= 299:
                                    if not (edge_dec >= 0.07 and win_prob >= 0.33):
                                        continue

                                # 🔴 Extreme Dogs (+300+)
                                elif odds >= 300:
                                    if not (edge_dec >= 0.15 and win_prob >= 0.33):
                                        continue

                                # 🔵 Small Favorites (-100 to -149)
                                elif -149 <= odds <= -100:
                                    if not (edge_dec >= 0.05 and win_prob >= 0.58):
                                        continue

                                # 🔵 Medium Favorites (-150 to -249)
                                elif -249 <= odds <= -150:
                                    if not (edge_dec >= 0.06 and win_prob >= 0.62):
                                        continue

                                # 🔵 Large Favorites (-250+)
                                elif odds <= -250:
                                    if not (edge_dec >= 0.07 and win_prob >= 0.70):
                                        continue

                                else:
                                    continue

                            # ---- NCAAB (UNCHANGED LOGIC) ----
                            else:
                                if not valid_edge(edge_dec, edge_pct):
                                    continue

                            selections.append({
                                "game_id": game_id,
                                "league": league,
                                "market": market,
                                "take_bet": f"{side}_ml",
                                "take_odds": american_odds,
                                "take_team": row.get(f"{side}_team"),
                                "value": win_prob,
                                "take_bet_edge_decimal": edge_dec,
                                "take_bet_edge_pct": edge_pct,
                            })

                    # =========================
                    # SPREAD (UNCHANGED)
                    # =========================

                    elif market == "spread":

                        for side in ["home", "away"]:

                            edge_dec = row.get(f"{side}_edge_decimal")
                            edge_pct = row.get(f"{side}_edge_pct")

                            if valid_edge(edge_dec, edge_pct):

                                selections.append({
                                    "game_id": game_id,
                                    "league": league,
                                    "market": market,
                                    "take_bet": f"{side}_spread",
                                    "take_odds": row.get(f"{side}_spread_juice_odds"),
                                    "take_team": row.get(f"{side}_team"),
                                    "value": row.get(f"{side}_spread"),
                                    "take_bet_edge_decimal": edge_dec,
                                    "take_bet_edge_pct": edge_pct,
                                })

                    # =========================
                    # TOTALS (UNCHANGED)
                    # =========================

                    elif market == "total":

                        over_dec = row.get("over_edge_decimal")
                        over_pct = row.get("over_edge_pct")

                        under_dec = row.get("under_edge_decimal")
                        under_pct = row.get("under_edge_pct")

                        total_value = row.get("total")

                        odds_over = row.get("total_over_juice_odds")
                        odds_under = row.get("total_under_juice_odds")

                        if valid_total_edge(over_dec, over_pct) and valid_total_odds(odds_over):

                            selections.append({
                                "game_id": game_id,
                                "league": league,
                                "market": market,
                                "take_bet": "over_bet",
                                "take_odds": odds_over,
                                "take_team": "over",
                                "value": total_value,
                                "take_bet_edge_decimal": over_dec,
                                "take_bet_edge_pct": over_pct,
                            })

                        if valid_total_edge(under_dec, under_pct) and valid_total_odds(odds_under):

                            selections.append({
                                "game_id": game_id,
                                "league": league,
                                "market": market,
                                "take_bet": "under_bet",
                                "take_odds": odds_under,
                                "take_team": "under",
                                "value": total_value,
                                "take_bet_edge_decimal": under_dec,
                                "take_bet_edge_pct": under_pct,
                            })

                sel_df = pd.DataFrame(selections)

                output_path = OUTPUT_DIR / input_path.name
                sel_df.to_csv(output_path, index=False)

                log.write(f"Wrote {output_path} | rows={len(sel_df)}\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()
