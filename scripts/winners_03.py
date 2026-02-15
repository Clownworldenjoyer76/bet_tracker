# scripts/winners_03.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import glob
import traceback

# =========================
# PATHS
# =========================

STEP_02_DIR = Path("docs/win/winners/step_02")
STEP_03_DIR = Path("docs/win/winners/step_03")
ERROR_DIR = Path("docs/win/errors/09_winners")
ERROR_LOG = ERROR_DIR / "winners_03.txt"

STEP_03_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONSTANTS
# =========================

OUTPUT_COLUMNS = [
    "date","time","away_team","home_team","league","game_id",
    "home_ml_edge","away_ml_edge","away_ml_odds","home_ml_odds",
    "away_spread","home_spread","home_spread_edge","away_spread_edge",
    "away_spread_odds","home_spread_odds",
    "over_edge","under_edge","over_odds","under_odds",
    "away_spread","home_spread","total","bet"
]

# =========================
# HELPERS
# =========================

def extract_date_from_filename(path):
    stem = Path(path).stem
    return stem.split("_")[-3] + "_" + stem.split("_")[-2] + "_" + stem.split("_")[-1]

def write_log(message, mode="w"):
    with open(ERROR_LOG, mode, encoding="utf-8") as f:
        f.write(message + "\n")

# =========================
# CORE
# =========================

def process_date(date_str):
    summary = []
    rows_out = []

    pattern = str(STEP_02_DIR / f"winners_*_{date_str}.csv")
    files = glob.glob(pattern)

    summary.append(f"=== WINNERS_03 RUN @ {datetime.utcnow().isoformat()}Z ===")
    summary.append(f"Date: {date_str}")
    summary.append(f"Files scanned: {len(files)}")

    for file_path in files:
        try:
            df = pd.read_csv(file_path)
            filename = Path(file_path).name

            is_ml = "_ml_" in filename
            is_spreads = "_spreads_" in filename
            is_totals = "_totals_" in filename

            for _, row in df.iterrows():
                bet_value = ""

                base = {
                    "date": row.get("date",""),
                    "time": row.get("time",""),
                    "away_team": row.get("away_team",""),
                    "home_team": row.get("home_team",""),
                    "league": row.get("league",""),
                    "game_id": row.get("game_id",""),
                    "home_ml_edge": "",
                    "away_ml_edge": "",
                    "away_ml_odds": "",
                    "home_ml_odds": "",
                    "away_spread": "",
                    "home_spread": "",
                    "home_spread_edge": "",
                    "away_spread_edge": "",
                    "away_spread_odds": "",
                    "home_spread_odds": "",
                    "over_edge": "",
                    "under_edge": "",
                    "over_odds": "",
                    "under_odds": "",
                    "total": "",
                    "bet": ""
                }

                if is_ml:
                    if row.get("deci_home_ml_juice_odds", 999) < row.get("deci_dk_home_odds", -1):
                        bet_value = "home_ml"
                    elif row.get("deci_away_ml_juice_odds", 999) < row.get("deci_dk_away_odds", -1):
                        bet_value = "away_ml"

                    base["home_ml_edge"] = row.get("home_ml_edge","")
                    base["away_ml_edge"] = row.get("away_ml_edge","")
                    base["away_ml_odds"] = row.get("away_ml_odds","")
                    base["home_ml_odds"] = row.get("home_ml_odds","")

                elif is_spreads:
                    if row.get("deci_home_spread_juice_odds", 999) < row.get("deci_dk_home_odds", -1):
                        bet_value = "home_spread"
                    elif row.get("deci_away_spread_juice_odds", 999) < row.get("deci_dk_away_odds", -1):
                        bet_value = "away_spread"

                    base["away_spread"] = row.get("away_spread","")
                    base["home_spread"] = row.get("home_spread","")
                    base["home_spread_edge"] = row.get("home_spread_edge","")
                    base["away_spread_edge"] = row.get("away_spread_edge","")
                    base["away_spread_odds"] = row.get("away_spread_odds","")
                    base["home_spread_odds"] = row.get("home_spread_odds","")

                elif is_totals:
                    if row.get("deci_over_juice_odds", 999) < row.get("deci_dk_over_odds", -1):
                        bet_value = "over_bet"
                    elif row.get("deci_under_juice_odds", 999) < row.get("deci_dk_under_odds", -1):
                        bet_value = "under_bet"

                    base["over_edge"] = row.get("over_edge","")
                    base["under_edge"] = row.get("under_edge","")
                    base["over_odds"] = row.get("over_odds","")
                    base["under_odds"] = row.get("under_odds","")
                    base["total"] = row.get("total","")

                if bet_value:
                    base["bet"] = bet_value
                    rows_out.append(base)

        except Exception:
            summary.append(f"ERROR processing {file_path}")
            summary.append(traceback.format_exc())

    out_path = STEP_03_DIR / f"winners_{date_str}.csv"

    if rows_out:
        out_df = pd.DataFrame(rows_out)
        out_df = out_df.reindex(columns=OUTPUT_COLUMNS)
        out_df.to_csv(out_path, index=False)
        summary.append(f"Rows written: {len(rows_out)}")
        summary.append(f"Wrote {out_path}")
    else:
        summary.append("Rows written: 0")

    write_log("\n".join(summary), mode="w")

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    # infer date from any step_02 file
    files = glob.glob(str(STEP_02_DIR / "winners_*_*.csv"))
    if not files:
        write_log("No input files found.", mode="w")
    else:
        latest = sorted(files)[-1]
        date_str = extract_date_from_filename(latest)
        process_date(date_str)
