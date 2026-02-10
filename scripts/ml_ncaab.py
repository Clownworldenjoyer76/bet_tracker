import pandas as pd
import glob
import os
from pathlib import Path
from datetime import datetime

# Constants
EDGE_NCAAB = 0.05
INPUT_DIR = Path("docs/win/dump/csvs/cleaned")
OUTPUT_DIR = Path("docs/win/ncaab/moneyline")
ERROR_DIR = Path("docs/win/errors/04moneyline")
ERROR_LOG = ERROR_DIR / "ml_ncaab_errors.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

def to_american(dec):
    if pd.isna(dec) or dec <= 1.01:
        return ""
    if dec >= 2.0:
        return f"+{int(round((dec - 1.0) * 100))}"
    return f"{int(round(-100.0 / (dec - 1.0)))}"

def log_error(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

def process_ncaab_files():
    files = glob.glob(str(INPUT_DIR / "ncaab_*.csv"))

    if not files:
        log_error(f"No NCAAB files found in {INPUT_DIR}")
        return

    for file_path in files:
        try:
            df = pd.read_csv(file_path)

            away_prob_col = "away_team_moneyline_win_prob"
            home_prob_col = "home_team_moneyline_win_prob"

            if away_prob_col not in df.columns or home_prob_col not in df.columns:
                log_error(f"{file_path} missing probability columns")
                continue

            # Force league value
            df["league"] = "ncaab_moneyline"

            # Away ML
            df["away_ml_fair_decimal_odds"] = (1 / df[away_prob_col]).round(2)
            df["away_ml_fair_american_odds"] = df["away_ml_fair_decimal_odds"].apply(to_american)
            df["away_ml_acceptable_decimal_odds"] = (df["away_ml_fair_decimal_odds"] * (1.0 + EDGE_NCAAB)).round(2)
            df["away_ml_acceptable_american_odds"] = df["away_ml_acceptable_decimal_odds"].apply(to_american)

            # Home ML
            df["home_ml_fair_decimal_odds"] = (1 / df[home_prob_col]).round(2)
            df["home_ml_fair_american_odds"] = df["home_ml_fair_decimal_odds"].apply(to_american)
            df["home_ml_acceptable_decimal_odds"] = (df["home_ml_fair_decimal_odds"] * (1.0 + EDGE_NCAAB)).round(2)
            df["home_ml_acceptable_american_odds"] = df["home_ml_acceptable_decimal_odds"].apply(to_american)

            cols_to_drop = [
                "fair_decimal_odds",
                "fair_american_odds",
                "acceptable_decimal_odds",
                "acceptable_american_odds",
            ]
            df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

            base_name = os.path.basename(file_path)
            output_path = OUTPUT_DIR / f"ml_{base_name}"
            df.to_csv(output_path, index=False)

        except Exception as e:
            log_error(f"{file_path} failed: {e}")

if __name__ == "__main__":
    process_ncaab_files()
