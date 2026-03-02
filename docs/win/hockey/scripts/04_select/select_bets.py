#!/usr/bin/env python3
# docs/win/hockey/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

INPUT_DIR = Path("docs/win/hockey/03_edges")
OUTPUT_DIR = Path("docs/win/hockey/04_select")
ERROR_DIR = Path("docs/win/hockey/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_MIN_EDGE_PCT = 0.03
TOTAL_MIN_PROB = 0.45

LEAGUE_CODE = "NHL"


def valid_edge(edge_pct, threshold):
    return pd.notna(edge_pct) and edge_pct >= threshold


def parse_game_id(game_id: str):
    """
    Expected format: YYYY_MM_DD_AWAY_TEAM_HOME_TEAM
    Example: 2026_03_01_Utah Mammoth_Chicago Blackhawks
    """
    if not isinstance(game_id, str) or not game_id:
        return "", "", ""

    parts = game_id.split("_")
    if len(parts) < 5:
        # Not enough parts to reliably parse
        return "", "", ""

    game_date = "_".join(parts[0:3])
    away_team = parts[3]
    home_team = "_".join(parts[4:])  # safer in case home team contains underscores someday

    return game_date, away_team, home_team


def main():
    with open(ERROR_LOG, "w") as log:

        log.write("=== NHL SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:

            moneyline_files = sorted(INPUT_DIR.glob("*_NHL_moneyline.csv"))
            puckline_files = sorted(INPUT_DIR.glob("*_NHL_puck_line.csv"))
            total_files = sorted(INPUT_DIR.glob("*_NHL_total.csv"))

            all_files = moneyline_files + puckline_files + total_files
            slates = {}

            for f in all_files:
                slate_key = (
                    f.name.replace("_NHL_moneyline.csv", "")
                    .replace("_NHL_puck_line.csv", "")
                    .replace("_NHL_total.csv", "")
                )
                slates.setdefault(slate_key, []).append(f)

            for slate_key in slates.keys():

                final_rows = []

                ml_count = 0
                puck_count = 0
                total_count = 0

                ml_path = INPUT_DIR / f"{slate_key}_NHL_moneyline.csv"
                pl_path = INPUT_DIR / f"{slate_key}_NHL_puck_line.csv"
                total_path = INPUT_DIR / f"{slate_key}_NHL_total.csv"

                ml_df = pd.read_csv(ml_path) if ml_path.exists() else None
                pl_df = pd.read_csv(pl_path) if pl_path.exists() else None
                total_df = pd.read_csv(total_path) if total_path.exists() else None

                game_ids = set()

                if ml_df is not None and "game_id" in ml_df.columns:
                    game_ids.update(ml_df["game_id"].dropna().unique())
                if pl_df is not None and "game_id" in pl_df.columns:
                    game_ids.update(pl_df["game_id"].dropna().unique())
                if total_df is not None and "game_id" in total_df.columns:
                    game_ids.update(total_df["game_id"].dropna().unique())

                for game_id in game_ids:

                    game_date, away_team, home_team = parse_game_id(game_id)

                    # =====================
                    # PUCK LINE
                    # =====================
                    if pl_df is not None:
                        game_pl = pl_df[pl_df["game_id"] == game_id]
                        best_row = None
                        best_edge = -float("inf")

                        for _, row in game_pl.iterrows():
                            for side in ["home", "away"]:
                                puck_line = row.get(f"{side}_puck_line")
                                edge_pct = row.get(f"{side}_edge_pct")

                                if pd.isna(puck_line) or puck_line <= 0:
                                    continue
                                if pd.isna(edge_pct) or edge_pct <= 0:
                                    continue

                                if edge_pct > best_edge:
                                    best_edge = edge_pct
                                    best_row = (row, side)

                        if best_row:
                            row, side = best_row
                            line_val = row.get(f"{side}_puck_line")

                            final_rows.append({
                                # join keys / normalization
                                "game_date": game_date,
                                "league": LEAGUE_CODE,
                                "away_team": away_team,
                                "home_team": home_team,
                                "market_type": "puck_line",
                                "bet_side": side,
                                "line": line_val,

                                # existing output fields (kept)
                                "game_id": game_id,
                                "take_bet": f"{side}_puck_line",
                                "take_bet_prob": row.get(f"{side}_juiced_prob_puck_line"),
                                "take_bet_edge_decimal": row.get(f"{side}_edge_decimal"),
                                "take_bet_edge_pct": row.get(f"{side}_edge_pct"),
                                "take_team": row.get(f"{side}_team"),
                                # ✅ sportsbook odds (NOT juiced)
                                "take_odds": row.get(f"{side}_dk_puck_line_american"),
                                "value": line_val,
                            })
                            puck_count += 1

                    # =====================
                    # MONEYLINE
                    # =====================
                    if ml_df is not None:
                        game_ml = ml_df[ml_df["game_id"] == game_id]
                        best_row = None
                        best_edge = -float("inf")

                        for _, row in game_ml.iterrows():
                            for side in ["home", "away"]:

                                edge_pct = row.get(f"{side}_edge_pct")
                                prob = row.get(f"{side}_prob")
                                # ✅ use sportsbook odds for tier logic
                                american_odds = row.get(f"{side}_dk_moneyline_american")

                                if pd.isna(edge_pct) or pd.isna(prob) or pd.isna(american_odds):
                                    continue

                                # --- Tier 1: +200 to +225 ---
                                if 200 <= american_odds <= 225:
                                    if edge_pct >= 0.05 and prob >= 0.35:
                                        pass
                                    else:
                                        continue

                                # --- Tier 2: +1 to +199 ---
                                elif 1 <= american_odds <= 199:
                                    if edge_pct >= 0.05 and prob >= 0.38:
                                        pass
                                    else:
                                        continue

                                # --- Tier 3: Favorites (-1 to -999) ---
                                elif -1 >= american_odds >= -999:
                                    if edge_pct >= 0.04 and prob >= 0.55:
                                        pass
                                    else:
                                        continue

                                else:
                                    continue

                                if edge_pct > best_edge:
                                    best_edge = edge_pct
                                    best_row = (row, side)

                        if best_row:
                            row, side = best_row

                            final_rows.append({
                                # join keys / normalization
                                "game_date": game_date,
                                "league": LEAGUE_CODE,
                                "away_team": away_team,
                                "home_team": home_team,
                                "market_type": "moneyline",
                                "bet_side": side,
                                "line": "",

                                # existing output fields (kept)
                                "game_id": game_id,
                                "take_bet": f"{side}_moneyline",
                                "take_bet_prob": row.get(f"{side}_prob"),
                                "take_bet_edge_decimal": row.get(f"{side}_edge_decimal"),
                                "take_bet_edge_pct": row.get(f"{side}_edge_pct"),
                                "take_team": row.get(f"{side}_team"),
                                # ✅ sportsbook odds (NOT juiced)
                                "take_odds": row.get(f"{side}_dk_moneyline_american"),
                                "value": row.get(f"{side}_prob"),
                            })
                            ml_count += 1

                    # =====================
                    # TOTAL
                    # =====================
                    if total_df is not None:
                        game_total = total_df[total_df["game_id"] == game_id]
                        best_row = None
                        best_edge = -float("inf")

                        for _, row in game_total.iterrows():
                            for side in ["over", "under"]:
                                edge_pct = row.get(f"{side}_edge_pct")
                                prob = row.get(f"juiced_total_{side}_prob")

                                if not valid_edge(edge_pct, TOTAL_MIN_EDGE_PCT):
                                    continue
                                if pd.isna(prob) or prob < TOTAL_MIN_PROB:
                                    continue

                                if edge_pct > best_edge:
                                    best_edge = edge_pct
                                    best_row = (row, side)

                        if best_row:
                            row, side = best_row
                            line_val = row.get("total")

                            final_rows.append({
                                # join keys / normalization
                                "game_date": game_date,
                                "league": LEAGUE_CODE,
                                "away_team": away_team,
                                "home_team": home_team,
                                "market_type": "total",
                                "bet_side": side,
                                "line": line_val,

                                # existing output fields (kept)
                                "game_id": game_id,
                                "take_bet": f"{side}_total",
                                "take_bet_prob": row.get(f"juiced_total_{side}_prob"),
                                "take_bet_edge_decimal": row.get(f"{side}_edge_decimal"),
                                "take_bet_edge_pct": row.get(f"{side}_edge_pct"),
                                "take_team": side,
                                # ✅ sportsbook odds (NOT juiced)
                                "take_odds": row.get(f"dk_total_{side}_american"),
                                "value": line_val,
                            })
                            total_count += 1

                out_df = pd.DataFrame(final_rows)

                if not out_df.empty:
                    out_df = out_df.sort_values(by="take_bet_edge_pct", ascending=False)

                output_path = OUTPUT_DIR / f"{slate_key}_NHL.csv"
                out_df.to_csv(output_path, index=False)

                log.write(f"Wrote {output_path} | rows={len(out_df)}\n")
                log.write(f"Moneyline bets: {ml_count}\n")
                log.write(f"Puck line bets: {puck_count}\n")
                log.write(f"Total bets: {total_count}\n\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()
