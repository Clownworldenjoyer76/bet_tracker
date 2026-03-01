# docs/win/hockey/scripts/01_merge/build_juice_files.py

#!/usr/bin/env python3

import pandas as pd
import glob
import math
import sys
import traceback
from pathlib import Path
from datetime import datetime
from scipy.stats import skellam

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/hockey/01_merge")
ERROR_DIR = Path("docs/win/hockey/errors/01_merge")
ERROR_LOG = ERROR_DIR / "build_juice_files.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

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


def poisson_cdf(k, lam):
    return sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))


# =========================
# MAIN
# =========================

def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as log:
        log.write("=== BUILD JUICE FILES RUN ===\n")
        log.write(f"{datetime.utcnow().isoformat()}Z\n\n")

    try:

        input_files = glob.glob(str(INPUT_DIR / "hockey_*.csv"))

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
            # TOTALS
            # =========================

            total_df = df.copy()

            total_df["dk_total_over_decimal"] = total_df["dk_total_over_american"].apply(american_to_decimal)
            total_df["dk_total_under_decimal"] = total_df["dk_total_under_american"].apply(american_to_decimal)

            fair_over = []
            fair_under = []

            for _, row in total_df.iterrows():
                lam = row["home_projected_goals"] + row["away_projected_goals"]
                T = row["total"]

                if pd.isna(T) or lam <= 0:
                    fair_over.append("")
                    fair_under.append("")
                    continue

                k = math.floor(T)
                p_under = poisson_cdf(k, lam)
                p_over = 1 - p_under

                fair_under.append(1/p_under if p_under > 0 else "")
                fair_over.append(1/p_over if p_over > 0 else "")

            total_df["fair_total_over_decimal"] = fair_over
            total_df["fair_total_under_decimal"] = fair_under

            total_output = INPUT_DIR / f"{game_date}_{market}_total.csv"
            total_df.to_csv(total_output, index=False)

            # =========================
            # PUCK LINE
            # =========================

            pl_df = df.copy()

            pl_df["away_dk_puck_line_decimal"] = pl_df["away_dk_puck_line_american"].apply(american_to_decimal)
            pl_df["home_dk_puck_line_decimal"] = pl_df["home_dk_puck_line_american"].apply(american_to_decimal)

            fair_home = []
            fair_away = []

            for _, row in pl_df.iterrows():
                lam_home = row["home_projected_goals"]
                lam_away = row["away_projected_goals"]

                if lam_home <= 0 or lam_away <= 0:
                    fair_home.append("")
                    fair_away.append("")
                    continue

                home_line = float(row["home_puck_line"])
                away_line = float(row["away_puck_line"])

                # HOME laying -1.5 (home must win by 2+)
                if home_line == -1.5:
                    p_home_minus = 1 - skellam.cdf(1, lam_home, lam_away)
                    p_away_plus = 1 - p_home_minus

                # AWAY laying -1.5 (away must win by 2+)
                elif away_line == -1.5:
                    # D = home_goals - away_goals
                    # away wins by 2+ <=> D <= -2
                    p_away_minus = skellam.cdf(-2, lam_home, lam_away)
                    p_home_plus = 1 - p_away_minus

                    p_home_minus = p_home_plus      # home +1.5
                    p_away_plus = p_away_minus     # away -1.5

                else:
                    fair_home.append("")
                    fair_away.append("")
                    continue

                fair_home.append(1/p_home_minus if p_home_minus > 0 else "")
                fair_away.append(1/p_away_plus if p_away_plus > 0 else "")

            pl_df["home_fair_puck_line_decimal"] = fair_home
            pl_df["away_fair_puck_line_decimal"] = fair_away

            pl_output = INPUT_DIR / f"{game_date}_{market}_puck_line.csv"
            pl_df.to_csv(pl_output, index=False)

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
