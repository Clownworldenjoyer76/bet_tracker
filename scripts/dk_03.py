# scripts/dk_03

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

ERROR_DIR = Path("docs/win/errors/03_dk_iv")
ERROR_LOG = ERROR_DIR / "dk_03.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def log(msg: str):
    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
        f.flush()

def norm(s: str) -> str:
    return " ".join(str(s).split()) if s else ""

def load_games_master():
    files = list(GAMES_MASTER_DIR.glob("games_*.csv"))
    if not files:
        raise RuntimeError("No games_master files found")

    return pd.concat(
        [pd.read_csv(f, dtype=str) for f in files],
        ignore_index=True
    )

# =========================
# CORE
# =========================

def process_file(path: Path, gm_df: pd.DataFrame):
    try:
        df = pd.read_csv(path, dtype=str)
        if df.empty:
            log(f"{path.name} | EMPTY FILE")
            return

        parts = path.stem.split("_")
        if len(parts) < 6:
            log(f"{path.name} | BAD FILENAME")
            return

        _, league, market, year, month, day = parts
        base_league = league.split("_")[0]
        date = f"{year}_{month}_{day}"

        gm_slice = gm_df[
            (gm_df["league"] == base_league) &
            (gm_df["date"] == date)
        ]

        out_rows = []

        for _, gm in gm_slice.iterrows():
            gid = gm["game_id"]

            # -------------------------
            # TOTALS (Over / Under rows)
            # -------------------------
            if market == "totals":
                game_rows = df[df["game_id"].isna() | (df["game_id"] == "")]

                sides = {
                    r["side"].lower(): r
                    for _, r in game_rows.iterrows()
                    if pd.notna(r.get("side"))
                }

                if "over" not in sides or "under" not in sides:
                    continue

                over = sides["over"]
                under = sides["under"]

                out_rows.append({
                    "date": over["date"],
                    "time": over["time"],
                    "league": over["league"],
                    "game_id": gid,
                    "away_team": gm["away_team"],
                    "home_team": gm["home_team"],
                    "total": over["total"],
                    "over_odds": over["odds"],
                    "under_odds": under["odds"],
                    "over_decimal_odds": over["decimal_odds"],
                    "under_decimal_odds": under["decimal_odds"],
                    "away_handle_pct": over.get("handle_pct"),
                    "home_handle_pct": under.get("handle_pct"),
                    "away_bets_pct": over.get("bets_pct"),
                    "home_bets_pct": under.get("bets_pct"),
                })

            # -------------------------
            # MONEYLINE / SPREADS
            # -------------------------
            else:
                df["team_norm"] = df["team"].apply(norm)
                df["opponent_norm"] = df["opponent"].apply(norm)

                away = norm(gm["away_team"])
                home = norm(gm["home_team"])

                game_rows = df[
                    df.apply(
                        lambda r: {r["team_norm"], r["opponent_norm"]} == {away, home},
                        axis=1,
                    )
                ]

                if len(game_rows) != 2:
                    continue

                row_map = {r["team_norm"]: r for _, r in game_rows.iterrows()}
                if away not in row_map or home not in row_map:
                    continue

                away_row = row_map[away]
                home_row = row_map[home]

                out = {
                    "date": away_row["date"],
                    "time": away_row["time"],
                    "league": away_row["league"],
                    "game_id": gid,
                    "away_team": away,
                    "home_team": home,
                    "away_handle_pct": away_row.get("handle_pct"),
                    "home_handle_pct": home_row.get("handle_pct"),
                    "away_bets_pct": away_row.get("bets_pct"),
                    "home_bets_pct": home_row.get("bets_pct"),
                }

                if market == "moneyline":
                    out.update({
                        "away_odds": away_row["odds"],
                        "home_odds": home_row["odds"],
                        "away_decimal_odds": away_row["decimal_odds"],
                        "home_decimal_odds": home_row["decimal_odds"],
                    })
                else:
                    out.update({
                        "away_spread": away_row["spread"],
                        "home_spread": home_row["spread"],
                        "away_odds": away_row["odds"],
                        "home_odds": home_row["odds"],
                        "away_decimal_odds": away_row["decimal_odds"],
                        "home_decimal_odds": home_row["decimal_odds"],
                    })

                out_rows.append(out)

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
    ERROR_DIR.mkdir(parents=True, exist_ok=True)

    # Hard reset log file every run
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("")

    log("DK_03 START")

    try:
        gm_df = load_games_master()

        for path in INPUT_DIR.glob("dk_*_*.csv"):
            process_file(path, gm_df)

        log("DK_03 END")

    except Exception as e:
        log("FATAL ERROR IN MAIN")
        log(str(e))
        log(traceback.format_exc())
        log("-" * 80)
        raise

if __name__ == "__main__":
    main()
