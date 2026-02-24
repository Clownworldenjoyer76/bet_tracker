# docs/win/basketball/scripts/01_merge/build_juice_files.py

#!/usr/bin/env python3

import pandas as pd
import glob
import math
import sys
import traceback
from pathlib import Path
from datetime import datetime
from scipy.stats import norm

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/01_merge")
ERROR_DIR = Path("docs/win/basketball/errors/01_merge")
ERROR_LOG = ERROR_DIR / "build_juice_files.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONSTANTS
# =========================

NBA_TOTAL_STD = 14
NBA_SPREAD_STD = 12

NCAAB_TOTAL_STD = 12
NCAAB_SPREAD_STD = 11

# =========================
# HELPERS
# =========================

def american_to_decimal(odds):
    if pd.isna(odds) or odds == "":
        return ""
    odds = float(odds)
    if odds > 0:
        return 1 + (odds / 100)
    return 1 + (100 / abs(odds))


def get_stds(market):
    if market == "NBA":
        return NBA_TOTAL_STD, NBA_SPREAD_STD
    return NCAAB_TOTAL_STD, NCAAB_SPREAD_STD


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as log:
        log.write("=== BUILD JUICE FILES RUN ===\n")
        log.write(f"{datetime.utcnow().isoformat()}Z\n\n")

    try:

        input_files = glob.glob(str(INPUT_DIR / "basketball_*.csv"))

        if not input_files:
            with open(ERROR_LOG, "a", encoding="utf-8") as log:
                log.write("No input files found.\n")
            return

        for file_path in input_files:

            df = pd.read_csv(file_path)

            if df.empty:
                continue

            game_date = df["game_date"].iloc[0]
            market = df["market"].iloc[0]

            total_std, spread_std = get_stds(market)

            # =========================
            # MONEYLINE
            # =========================

            ml_df = df.copy()

            ml_df["away_dk_decimal_moneyline"] = ml_df["away_dk_moneyline_american"].apply(american_to_decimal)
            ml_df["home_dk_decimal_moneyline"] = ml_df["home_dk_moneyline_american"].apply(american_to_decimal)

            ml_df["away_fair_decimal_moneyline"] = ml_df["away_prob"].apply(lambda x: 1/x if x > 0 else "")
            ml_df["home_fair_decimal_moneyline"] = ml_df["home_prob"].apply(lambda x: 1/x if x > 0 else "")

            ml_output = INPUT_DIR / f"{game_date}_{market}_moneyline.csv"
            ml_df.to_csv(ml_output, index=False)

            # =========================
            # TOTALS (Normal Distribution)
            # =========================

            total_df = df.copy()

            total_df["dk_total_over_decimal"] = total_df["dk_total_over_american"].apply(american_to_decimal)
            total_df["dk_total_under_decimal"] = total_df["dk_total_under_american"].apply(american_to_decimal)

            fair_over = []
            fair_under = []

            for _, row in total_df.iterrows():

                mean = row["total_projected_points"]
                T = row["total"]

                if pd.isna(T):
                    fair_over.append("")
                    fair_under.append("")
                    continue

                z = (T - mean) / total_std
                p_under = norm.cdf(z)
                p_over = 1 - p_under

                fair_under.append(1/p_under if p_under > 0 else "")
                fair_over.append(1/p_over if p_over > 0 else "")

            total_df["fair_total_over_decimal"] = fair_over
            total_df["fair_total_under_decimal"] = fair_under

            total_output = INPUT_DIR / f"{game_date}_{market}_total.csv"
            total_df.to_csv(total_output, index=False)

            # =========================
            # SPREAD (Normal Distribution)
            # =========================

            spread_df = df.copy()

            spread_df["away_dk_spread_decimal"] = spread_df["away_dk_spread_american"].apply(american_to_decimal)
            spread_df["home_dk_spread_decimal"] = spread_df["home_dk_spread_american"].apply(american_to_decimal)

            fair_home = []
            fair_away = []

            for _, row in spread_df.iterrows():

                mean_margin = row["home_projected_points"] - row["away_projected_points"]

                try:
                    home_line = float(row["home_spread"])
                except:
                    fair_home.append("")
                    fair_away.append("")
                    continue

                z = (home_line - mean_margin) / spread_std
                p_home_cover = 1 - norm.cdf(z)
                p_away_cover = 1 - p_home_cover

                fair_home.append(1/p_home_cover if p_home_cover > 0 else "")
                fair_away.append(1/p_away_cover if p_away_cover > 0 else "")

            spread_df["home_fair_spread_decimal"] = fair_home
            spread_df["away_fair_spread_decimal"] = fair_away

            spread_output = INPUT_DIR / f"{game_date}_{market}_spread.csv"
            spread_df.to_csv(spread_output, index=False)

            with open(ERROR_LOG, "a", encoding="utf-8") as log:
                log.write(f"Processed {file_path}\n")

        with open(ERROR_LOG, "a", encoding="utf-8") as log:
            log.write("\nCompleted successfully.\n")

    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as log:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
