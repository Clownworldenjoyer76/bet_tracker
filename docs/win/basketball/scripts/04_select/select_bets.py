#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# FILTER RULES
# =========================

MIN_EDGE_DECIMAL = 0.05
MIN_EDGE_PCT = 0.02

# =========================
# HELPERS
# =========================

def valid_edge(edge_dec, edge_pct):
    return (
        pd.notna(edge_dec)
        and pd.notna(edge_pct)
        and edge_dec >= MIN_EDGE_DECIMAL
        and edge_pct >= MIN_EDGE_PCT
    )

# =========================
# MAIN
# =========================

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

                for _, row in df.iterrows():

                    league = str(row.get("league", "")).lower()
                    market = str(row.get("market", "")).lower()

                    game_id = row.get("game_id")

                    # =========================
                    # MONEYLINE
                    # =========================

                    if market == "moneyline":

                        for side in ["home", "away"]:

                            edge_dec = row.get(f"{side}_edge_decimal")
                            edge_pct = row.get(f"{side}_edge_pct")

                            if valid_edge(edge_dec, edge_pct):

                                selections.append({
                                    "game_id": game_id,
                                    "league": row.get("league"),
                                    "market": market,
                                    "take_bet": f"{side}_ml",
                                    "take_bet_edge_decimal": edge_dec,
                                    "take_bet_edge_pct": edge_pct,
                                })

                    # =========================
                    # SPREAD
                    # =========================

                    elif market == "spread":

                        for side in ["home", "away"]:

                            edge_dec = row.get(f"{side}_edge_decimal")
                            edge_pct = row.get(f"{side}_edge_pct")

                            if valid_edge(edge_dec, edge_pct):

                                selections.append({
                                    "game_id": game_id,
                                    "league": row.get("league"),
                                    "market": market,
                                    "take_bet": f"{side}_spread",
                                    "take_bet_edge_decimal": edge_dec,
                                    "take_bet_edge_pct": edge_pct,
                                })

                    # =========================
                    # TOTALS
                    # =========================

                    elif market == "total":

                        total = row.get("total")
                        total_diff = row.get("total_diff")

                        # OVER
                        over_dec = row.get("over_edge_decimal")
                        over_pct = row.get("over_edge_pct")

                        # UNDER
                        under_dec = row.get("under_edge_decimal")
                        under_pct = row.get("under_edge_pct")

                        # ---- Special NCAAB totals over logic ----
                        is_ncaab = "ncaab" in league

                        if is_ncaab:

                            if (
                                pd.notna(total)
                                and pd.notna(total_diff)
                                and pd.notna(over_dec)
                            ):

                                abs_diff = abs(total_diff)

                                if total < 150:
                                    if over_dec >= 0.40 and abs_diff >= 4:
                                        selections.append({
                                            "game_id": game_id,
                                            "league": row.get("league"),
                                            "market": market,
                                            "take_bet": "over_bet",
                                            "take_bet_edge_decimal": over_dec,
                                            "take_bet_edge_pct": over_pct,
                                        })

                                elif total > 150:
                                    if abs_diff >= 2:
                                        selections.append({
                                            "game_id": game_id,
                                            "league": row.get("league"),
                                            "market": market,
                                            "take_bet": "over_bet",
                                            "take_bet_edge_decimal": over_dec,
                                            "take_bet_edge_pct": over_pct,
                                        })

                        # ---- Normal totals logic (all leagues, including under) ----

                        # Over (non-special cases)
                        if valid_edge(over_dec, over_pct):
                            selections.append({
                                "game_id": game_id,
                                "league": row.get("league"),
                                "market": market,
                                "take_bet": "over_bet",
                                "take_bet_edge_decimal": over_dec,
                                "take_bet_edge_pct": over_pct,
                            })

                        # Under
                        if valid_edge(under_dec, under_pct):
                            selections.append({
                                "game_id": game_id,
                                "league": row.get("league"),
                                "market": market,
                                "take_bet": "under_bet",
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
