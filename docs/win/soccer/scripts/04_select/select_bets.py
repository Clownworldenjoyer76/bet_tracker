#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

INPUT_DIR = Path("docs/win/soccer/03_edges")
OUTPUT_DIR = Path("docs/win/soccer/04_select")
ERROR_DIR = Path("docs/win/soccer/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

MIN_EDGE_PCT = 0.03
DRAW_MIN_EDGE_PCT = 0.05
DRAW_MIN_PROB = 0.22
DRAW_DOMINANCE_MARGIN = 0.03


def parse_match_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p")
    except Exception:
        return None


def main():

    with open(ERROR_LOG, "w") as log:

        log.write("=== SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:

            input_files = sorted(INPUT_DIR.glob("soccer_*.csv"))

            if not input_files:
                log.write("No input files found.\n")
                return

            for input_path in input_files:

                df = pd.read_csv(input_path)

                required_cols = [
                    "league","market","match_date","match_time",
                    "home_team","away_team",
                    "home_prob","draw_prob","away_prob",
                    "home_edge_pct","draw_edge_pct","away_edge_pct",
                    "home_american","draw_american","away_american",
                    "game_id"
                ]

                for col in required_cols:
                    if col not in df.columns:
                        raise ValueError(f"Missing column: {col}")

                selections = []

                for _, row in df.iterrows():

                    edges = {
                        "home": row["home_edge_pct"],
                        "draw": row["draw_edge_pct"],
                        "away": row["away_edge_pct"]
                    }

                    probs = {
                        "home": row["home_prob"],
                        "draw": row["draw_prob"],
                        "away": row["away_prob"]
                    }

                    for k in list(edges.keys()):
                        if pd.isna(edges[k]):
                            edges[k] = -999

                    positive_edges = {k: v for k, v in edges.items() if v >= MIN_EDGE_PCT}

                    if not positive_edges:
                        continue

                    best_side = max(positive_edges, key=positive_edges.get)
                    best_edge = positive_edges[best_side]

                    if best_side == "draw":

                        sorted_edges = sorted(edges.values(), reverse=True)
                        second_best = sorted_edges[1] if len(sorted_edges) > 1 else -999

                        if (
                            best_edge < DRAW_MIN_EDGE_PCT
                            or probs["draw"] < DRAW_MIN_PROB
                            or (best_edge - second_best) < DRAW_DOMINANCE_MARGIN
                        ):

                            non_draw_positive = {
                                k: v for k, v in positive_edges.items() if k != "draw"
                            }

                            if not non_draw_positive:
                                continue

                            best_side = max(non_draw_positive, key=non_draw_positive.get)
                            best_edge = non_draw_positive[best_side]

                    selections.append({

                        "league": row["league"],
                        "market": row["market"],
                        "match_date": row["match_date"],
                        "match_time": row["match_time"],
                        "home_team": row["home_team"],
                        "away_team": row["away_team"],

                        "home_prob": row["home_prob"],
                        "draw_prob": row["draw_prob"],
                        "away_prob": row["away_prob"],

                        "game_id": row["game_id"],

                        "take_bet": best_side,
                        "take_bet_prob": row[f"{best_side}_prob"],
                        "take_bet_edge_pct": row[f"{best_side}_edge_pct"],

                        "home_american": row["home_american"],
                        "draw_american": row["draw_american"],
                        "away_american": row["away_american"],
                    })

                sel_df = pd.DataFrame(selections)

                if not sel_df.empty:

                    sel_df["_sort_time"] = sel_df["match_time"].apply(parse_match_time)
                    sel_df = sel_df.sort_values(by="_sort_time")
                    sel_df = sel_df.drop(columns=["_sort_time"])

                output_path = OUTPUT_DIR / input_path.name
                sel_df.to_csv(output_path, index=False)

                log.write(f"Wrote {output_path}\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()
