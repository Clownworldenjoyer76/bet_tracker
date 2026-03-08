#!/usr/bin/env python3
# docs/win/basketball/scripts/01_merge/build_juice_files.py

import pandas as pd
import glob
import sys
import traceback
from pathlib import Path
from datetime import datetime
from scipy.stats import norm, poisson

# ============================================================
# SETTINGS
# ============================================================

# ------------------------------------------------------------
# NBA SETTINGS
# ------------------------------------------------------------

NBA_EDGE = 0.06
NBA_TOTAL_EDGE = 0.05
NBA_SPREAD_EDGE = 0.06

NBA_TOTAL_STD = 22.7
NBA_SPREAD_STD = 13.7


# ------------------------------------------------------------
# NCAAB SETTINGS
# ------------------------------------------------------------

NCAAB_EDGE = 0.06
NCAAB_TOTAL_EDGE = 0.15
NCAAB_SPREAD_EDGE = 0.06

NCAAB_TOTAL_STD = 18.6662
NCAAB_SPREAD_STD = 16.0642


# ============================================================
# LOGGER
# ============================================================

def audit(log_path, stage, status, msg="", df=None):

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")

        if msg:
            f.write(f"MSG: {msg}\n")

        if df is not None:
            f.write(f"ROWS: {len(df)}\n")

        f.write("-"*40+"\n")


# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path("docs/win/basketball/01_merge")
ERROR_DIR = Path("docs/win/basketball/errors/01_merge")
ERROR_LOG = ERROR_DIR / "build_juice_files.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def american_to_decimal(odds):

    if pd.isna(odds) or odds == "":
        return ""

    odds = float(odds)

    if odds > 0:
        return 1 + (odds / 100)

    return 1 + (100 / abs(odds))


def to_american(dec):

    if pd.isna(dec) or dec <= 1:
        return ""

    if dec >= 2:
        return f"+{int((dec - 1) * 100)}"

    return f"-{int(100 / (dec - 1))}"


def clamp_probability(p):

    return min(max(p, 0.05), 0.95)


def get_market_settings(market):

    if market == "NBA":

        return {
            "ML_EDGE": NBA_EDGE,
            "TOTAL_EDGE": NBA_TOTAL_EDGE,
            "SPREAD_EDGE": NBA_SPREAD_EDGE,
            "TOTAL_STD": NBA_TOTAL_STD,
            "SPREAD_STD": NBA_SPREAD_STD
        }

    return {
        "ML_EDGE": NCAAB_EDGE,
        "TOTAL_EDGE": NCAAB_TOTAL_EDGE,
        "SPREAD_EDGE": NCAAB_SPREAD_EDGE,
        "TOTAL_STD": NCAAB_TOTAL_STD,
        "SPREAD_STD": NCAAB_SPREAD_STD
    }


# ============================================================
# MAIN
# ============================================================

def main():

    with open(ERROR_LOG, "w") as log:
        log.write("=== BUILD JUICE FILES RUN ===\n")
        log.write(f"{datetime.utcnow().isoformat()}Z\n\n")

    try:

        input_files = glob.glob(str(INPUT_DIR / "basketball_*.csv"))

        if not input_files:
            print("No files found")
            return

        for file_path in input_files:

            df = pd.read_csv(file_path)

            if df.empty:
                continue

            market = df["market"].iloc[0]
            game_date = df["game_date"].iloc[0]

            settings = get_market_settings(market)

            ML_EDGE = settings["ML_EDGE"]
            TOTAL_EDGE = settings["TOTAL_EDGE"]
            SPREAD_EDGE = settings["SPREAD_EDGE"]
            TOTAL_STD = settings["TOTAL_STD"]
            SPREAD_STD = settings["SPREAD_STD"]

            # =====================================================
            # MONEYLINE
            # =====================================================

            ml_df = df.copy()

            ml_df["away_decimal"] = ml_df["away_dk_moneyline_american"].apply(american_to_decimal)
            ml_df["home_decimal"] = ml_df["home_dk_moneyline_american"].apply(american_to_decimal)

            ml_df["away_fair"] = 1 / ml_df["away_prob"]
            ml_df["home_fair"] = 1 / ml_df["home_prob"]

            ml_df["away_acceptable"] = ml_df["away_fair"] * (1 + ML_EDGE)
            ml_df["home_acceptable"] = ml_df["home_fair"] * (1 + ML_EDGE)

            ml_df["away_acceptable_american"] = ml_df["away_acceptable"].apply(to_american)
            ml_df["home_acceptable_american"] = ml_df["home_acceptable"].apply(to_american)

            ml_output = INPUT_DIR / f"{game_date}_{market}_moneyline.csv"

            ml_df.to_csv(ml_output, index=False)

            audit(ERROR_LOG, "ML", "SUCCESS", file_path, ml_df)

            # =====================================================
            # TOTALS
            # =====================================================

            total_df = df.copy()

            fair_over = []
            fair_under = []

            acc_over = []
            acc_under = []

            for _, row in total_df.iterrows():

                T = row["total"]
                mean = row["total_projected_points"]

                if pd.isna(T):

                    fair_over.append("")
                    fair_under.append("")
                    acc_over.append("")
                    acc_under.append("")
                    continue

                if market == "NCAAB":

                    p_under = poisson.cdf(T - 0.5, mean)

                else:

                    z = (T - mean) / TOTAL_STD
                    p_under = norm.cdf(z)

                p_under = clamp_probability(p_under)
                p_over = 1 - p_under

                fair_under_dec = 1 / p_under
                fair_over_dec = 1 / p_over

                fair_under.append(fair_under_dec)
                fair_over.append(fair_over_dec)

                acc_under_dec = fair_under_dec * (1 + TOTAL_EDGE)
                acc_over_dec = fair_over_dec * (1 + TOTAL_EDGE)

                acc_under.append(acc_under_dec)
                acc_over.append(acc_over_dec)

            total_df["fair_over"] = fair_over
            total_df["fair_under"] = fair_under

            total_df["acceptable_over"] = acc_over
            total_df["acceptable_under"] = acc_under

            total_output = INPUT_DIR / f"{game_date}_{market}_total.csv"

            total_df.to_csv(total_output, index=False)

            audit(ERROR_LOG, "TOTAL", "SUCCESS", file_path, total_df)

            # =====================================================
            # SPREAD
            # =====================================================

            spread_df = df.copy()

            fair_home = []
            fair_away = []

            acc_home = []
            acc_away = []

            for _, row in spread_df.iterrows():

                mean_margin = row["home_projected_points"] - row["away_projected_points"]

                try:
                    home_line = float(row["home_spread"])
                except:
                    fair_home.append("")
                    fair_away.append("")
                    acc_home.append("")
                    acc_away.append("")
                    continue

                p_home = 1 - norm.cdf(-home_line, mean_margin, SPREAD_STD)

                p_home = clamp_probability(p_home)

                p_away = 1 - p_home

                fair_home_dec = 1 / p_home
                fair_away_dec = 1 / p_away

                fair_home.append(fair_home_dec)
                fair_away.append(fair_away_dec)

                acc_home_dec = fair_home_dec * (1 + SPREAD_EDGE)
                acc_away_dec = fair_away_dec * (1 + SPREAD_EDGE)

                acc_home.append(acc_home_dec)
                acc_away.append(acc_away_dec)

            spread_df["home_fair"] = fair_home
            spread_df["away_fair"] = fair_away

            spread_df["home_acceptable"] = acc_home
            spread_df["away_acceptable"] = acc_away

            spread_output = INPUT_DIR / f"{game_date}_{market}_spread.csv"

            spread_df.to_csv(spread_output, index=False)

            audit(ERROR_LOG, "SPREAD", "SUCCESS", file_path, spread_df)

        print("Build juice files complete")

    except Exception as e:

        with open(ERROR_LOG, "a") as log:

            log.write("\nERROR\n")
            log.write(str(e))
            log.write("\n\n")
            log.write(traceback.format_exc())

        sys.exit(1)


if __name__ == "__main__":
    main()
