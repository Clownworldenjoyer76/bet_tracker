# scripts/dk_03.py

#!/usr/bin/env python3

import csv
from pathlib import Path
import traceback
import pandas as pd

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/cleaned")
OUTPUT_DIR = Path("docs/win/manual/normalized")
GAMES_MASTER_DIR = Path("docs/win/games_master")

ERROR_DIR = Path("docs/win/errors/02_dk_prep")
ERROR_LOG = ERROR_DIR / "dk_03.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def log(msg: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def load_games_master():
    files = GAMES_MASTER_DIR.glob("games_*.csv")
    return pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)

# =========================
# CORE
# =========================

def process_file(path: Path, gm_df):
    try:
        df = pd.read_csv(path, dtype=str)
        if df.empty:
            return

        parts = path.stem.split("_")
        _, league, market, *_ = parts

        out_rows = []

        for gid, gdf in df.groupby("game_id"):
            if not gid:
                log(f"EMPTY game_id in {path.name}")
                continue

            gm = gm_df[gm_df["game_id"] == gid]
            if gm.empty:
                log(f"UNKNOWN game_id {gid}")
                continue

            away = gm.iloc[0]["away_team"]
            home = gm.iloc[0]["home_team"]

            if market in ("moneyline", "spreads"):
                if len(gdf) != 2:
                    log(f"{gid} expected 2 rows, found {len(gdf)}")
                    continue

                row_map = {r["team"]: r for _, r in gdf.iterrows()}
                if away not in row_map or home not in row_map:
                    log(f"{gid} team mismatch")
                    continue

                out = {
                    "date": gdf.iloc[0]["date"],
                    "time": gdf.iloc[0]["time"],
                    "league": gdf.iloc[0]["league"],
                    "game_id": gid,
                    "away_team": away,
                    "home_team": home,
                    "away_handle_pct": row_map[away].get("handle_pct"),
                    "home_handle_pct": row_map[home].get("handle_pct"),
                    "away_bets_pct": row_map[away].get("bets_pct"),
                    "home_bets_pct": row_map[home].get("bets_pct"),
                }

                if market == "moneyline":
                    out.update({
                        "away_odds": row_map[away]["odds"],
                        "home_odds": row_map[home]["odds"],
                        "away_decimal_odds": row_map[away]["decimal_odds"],
                        "home_decimal_odds": row_map[home]["decimal_odds"],
                    })
                else:
                    out.update({
                        "away_spread": row_map[away]["spread"],
                        "home_spread": row_map[home]["spread"],
                        "away_odds": row_map[away]["odds"],
                        "home_odds": row_map[home]["odds"],
                        "away_decimal_odds": row_map[away]["decimal_odds"],
                        "home_decimal_odds": row_map[home]["decimal_odds"],
                    })

                out_rows.append(out)

            elif market == "totals":
                sides = {r["side"].lower(): r for _, r in gdf.iterrows()}
                if "over" not in sides or "under" not in sides:
                    log(f"{gid} missing over/under")
                    continue

                out_rows.append({
                    "date": gdf.iloc[0]["date"],
                    "time": gdf.iloc[0]["time"],
                    "league": gdf.iloc[0]["league"],
                    "game_id": gid,
                    "away_team": away,
                    "home_team": home,
                    "total": sides["over"]["total"],
                    "over_odds": sides["over"]["odds"],
                    "under_odds": sides["under"]["odds"],
                    "over_decimal_odds": sides["over"]["decimal_odds"],
                    "under_decimal_odds": sides["under"]["decimal_odds"],
                })

            else:
                log(f"UNKNOWN market {market}")

        if out_rows:
            out_path = OUTPUT_DIR / path.name
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
                writer.writeheader()
                writer.writerows(out_rows)

        log(f"{path.name} | games_out={len(out_rows)}")

    except Exception as e:
        log(f"FILE ERROR: {path.name}")
        log(str(e))
        log(traceback.format_exc())
        log("-" * 80)

# =========================
# MAIN
# =========================

def main():
    log("DK_03 START")
    gm_df = load_games_master()

    for path in INPUT_DIR.glob("dk_*_*.csv"):
        process_file(path, gm_df)

    log("DK_03 END\n")

if __name__ == "__main__":
    main()
