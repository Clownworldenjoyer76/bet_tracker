#!/usr/bin/env python3
# docs/win/hockey/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback
import yaml

# =========================
# PATHS
# =========================
INPUT_DIR = Path("docs/win/hockey/03_edges")
OUTPUT_DIR = Path("docs/win/hockey/04_select")
CONFIG_PATH = Path("docs/win/hockey/config/markets.yaml")

ERROR_DIR = Path("docs/win/hockey/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE_CODE = "NHL"

# =========================
# LOAD CONFIG
# =========================
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)["markets"]["nhl"]

# =========================
# HELPERS
# =========================
def f(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None

# =========================
# TOTAL
# =========================
def process_total(row, config):

    results = []
    selected_side = None

    for side in ["over", "under"]:

        side_config = config[side]

        edge = f(row.get(f"{side}_edge_pct"))
        prob = f(row.get(f"juiced_total_{side}_prob"))
        line = row.get("total")

        if edge is None or prob is None:
            continue

        if edge >= side_config["min_edge"] and prob >= side_config["min_prob"]:
            selected_side = side

            results.append({
                "market_type": "total",
                "bet_side": side,
                "line": line,
                "take_bet": f"{side}_total",
                "take_bet_edge_pct": edge,
                "take_odds": row.get(f"dk_total_{side}_american"),
                "selected_total_side": side
            })

    return results, selected_side

# =========================
# PUCK LINE
# =========================
def process_puck_line(row, config, selected_total_side):

    results = []

    for side in ["home", "away"]:

        line = f(row.get(f"{side}_puck_line"))
        edge = f(row.get(f"{side}_edge_pct"))
        prob = f(row.get(f"{side}_prob"))
        odds = f(row.get(f"{side}_dk_puck_line_american"))

        if line is None:
            continue

        keep = False

        # DOG
        if line >= 1.5:
            if prob is not None and prob >= config["dog"]["min_prob"]:
                keep = True

        # FAVORITE
        elif line <= -1.5:

            # block rule
            if selected_total_side == "under":
                continue

            if (
                edge is not None and
                edge >= config["favorite"]["min_edge"] and
                odds is not None and
                odds >= config["favorite"]["max_odds"]
            ):
                keep = True

        if keep:
            results.append({
                "market_type": "puck_line",
                "bet_side": side,
                "line": line,
                "take_bet": f"{side}_puck_line",
                "take_bet_edge_pct": edge,
                "take_odds": odds
            })

    return results

# =========================
# MONEYLINE
# =========================
def process_moneyline(row, config):

    results = []

    for side in ["home", "away"]:

        edge = f(row.get(f"{side}_edge_pct"))
        prob = f(row.get(f"{side}_prob"))
        odds = f(row.get(f"{side}_dk_moneyline_american"))

        if edge is None or prob is None or odds is None:
            continue

        if not (config["odds_range"][0] <= odds <= config["odds_range"][1]):
            continue

        keep = False

        # favorite logic
        if odds < 0:
            if edge >= config["favorite"]["min_edge"] and prob >= config["favorite"]["min_prob"]:
                keep = True

        # standard logic
        else:
            if edge >= config["standard"]["min_edge"] and prob >= config["standard"]["min_prob"]:
                keep = True

        if keep:
            results.append({
                "market_type": "moneyline",
                "bet_side": side,
                "line": "",
                "take_bet": f"{side}_moneyline",
                "take_bet_edge_pct": edge,
                "take_odds": odds
            })

    return results

# =========================
# MAIN
# =========================
def main():

    with open(ERROR_LOG, "w") as log:

        log.write("=== NHL SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:

            all_files = sorted(INPUT_DIR.glob("*_NHL_*.csv"))
            slates = {}

            for fpath in all_files:
                slate_key = fpath.name.split('_NHL_')[0]
                slates.setdefault(slate_key, []).append(fpath)

            for slate_key in slates:

                final_rows = []
                seen = set()

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

                    # TOTAL
                    if td_df is not None:
                        game_tot = td_df[(td_df["away_team"] == away) & (td_df["home_team"] == home)]
                        for _, trow in game_tot.iterrows():
                            totals, selected_total_side = process_total(trow, CONFIG["total"])

                            for t in totals:
                                key = f"{game_date}_{away}_{home}_{t['market_type']}_{t['bet_side']}"
                                if key not in seen:
                                    t.update({
                                        "game_date": game_date,
                                        "league": LEAGUE_CODE,
                                        "away_team": away,
                                        "home_team": home,
                                        "game_id": game_id
                                    })
                                    final_rows.append(t)
                                    seen.add(key)

                    # PUCK LINE
                    for p in process_puck_line(row, CONFIG["puck_line"], selected_total_side):
                        key = f"{game_date}_{away}_{home}_{p['market_type']}_{p['bet_side']}"
                        if key not in seen:
                            p.update({
                                "game_date": game_date,
                                "league": LEAGUE_CODE,
                                "away_team": away,
                                "home_team": home,
                                "game_id": game_id
                            })
                            final_rows.append(p)
                            seen.add(key)

                    # MONEYLINE
                    if ml_df is not None:
                        game_ml = ml_df[(ml_df["away_team"] == away) & (ml_df["home_team"] == home)]
                        for _, mrow in game_ml.iterrows():
                            for m in process_moneyline(mrow, CONFIG["moneyline"]):
                                key = f"{game_date}_{away}_{home}_{m['market_type']}_{m['bet_side']}"
                                if key not in seen:
                                    m.update({
                                        "game_date": game_date,
                                        "league": LEAGUE_CODE,
                                        "away_team": away,
                                        "home_team": home,
                                        "game_id": game_id
                                    })
                                    final_rows.append(m)
                                    seen.add(key)

                if final_rows:
                    df = pd.DataFrame(final_rows)
                    out_path = OUTPUT_DIR / f"{slate_key}_NHL.csv"
                    df.to_csv(out_path, index=False)

                    log.write(f"Wrote {out_path.name} ({len(df)} rows)\n")

        except Exception as e:
            log.write(f"CRITICAL ERROR: {str(e)}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
