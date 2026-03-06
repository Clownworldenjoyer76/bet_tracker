#!/usr/bin/env python3
# docs/win/hockey/scripts/model_testing/build_juice_files.py

import pandas as pd
import glob
import math
import sys
import traceback
from pathlib import Path
from datetime import datetime
from scipy.stats import skellam

OVERRIDE_CONFIG_PATH = Path("docs/win/hockey/model_testing/rule_config.py")


def load_override_config():
    if not OVERRIDE_CONFIG_PATH.exists():
        return {}

    scope = {}
    try:
        content = OVERRIDE_CONFIG_PATH.read_text(encoding="utf-8")
        exec(compile(content, str(OVERRIDE_CONFIG_PATH), "exec"), {}, scope)
        return {k: v for k, v in scope.items() if not k.startswith("__")}
    except Exception:
        return {}


OVR = load_override_config()

INPUT_DIR = Path("docs/win/hockey/01_merge")
ERROR_DIR = Path("docs/win/hockey/errors/01_merge")
ERROR_LOG = ERROR_DIR / "build_juice_files.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

HOME_PROB_TOL = 0.0
PUCK_LINE_BINARY_SEARCH_STEPS = 60
POISSON_TOTAL_FLOOR_SHIFT = 0.0

if "HOME_PROB_TOL" in OVR:
    HOME_PROB_TOL = float(OVR["HOME_PROB_TOL"])

if "PUCK_LINE_BINARY_SEARCH_STEPS" in OVR:
    PUCK_LINE_BINARY_SEARCH_STEPS = int(OVR["PUCK_LINE_BINARY_SEARCH_STEPS"])

if "POISSON_TOTAL_FLOOR_SHIFT" in OVR:
    POISSON_TOTAL_FLOOR_SHIFT = float(OVR["POISSON_TOTAL_FLOOR_SHIFT"])


def american_to_decimal(odds):
    if pd.isna(odds) or odds == "":
        return ""
    odds = float(odds)
    if odds > 0:
        return 1 + (odds / 100)
    return 1 + (100 / abs(odds))


def poisson_cdf(k, lam):
    return sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))


def safe_inverse_probability(x):
    if pd.notna(x) and x > 0:
        return 1 / x
    return ""


def main():

    with open(ERROR_LOG, "w", encoding="utf-8") as log:
        log.write("=== BUILD JUICE FILES RUN ===\n")
        log.write(f"{datetime.utcnow().isoformat()}Z\n\n")

    try:

        input_files = sorted(glob.glob(str(INPUT_DIR / "*_NHL_*.csv")))

        if not input_files:
            with open(ERROR_LOG, "a", encoding="utf-8") as log:
                log.write("No input files found.\n")
            return

        for file_path in input_files:

            df = pd.read_csv(file_path)

            if df.empty:
                continue

            df["home_prob"] = pd.to_numeric(df["home_prob"], errors="coerce")
            df["away_prob"] = pd.to_numeric(df["away_prob"], errors="coerce")
            df["home_projected_goals"] = pd.to_numeric(df["home_projected_goals"], errors="coerce")
            df["away_projected_goals"] = pd.to_numeric(df["away_projected_goals"], errors="coerce")
            df["total_projected_goals"] = pd.to_numeric(df["total_projected_goals"], errors="coerce")
            df["total"] = pd.to_numeric(df["total"], errors="coerce")
            df["home_puck_line"] = pd.to_numeric(df["home_puck_line"], errors="coerce")
            df["away_puck_line"] = pd.to_numeric(df["away_puck_line"], errors="coerce")

            game_date = df["game_date"].iloc[0]
            market = df["market"].iloc[0]

            ml_df = df.copy()

            ml_df["away_dk_decimal_moneyline"] = ml_df["away_dk_moneyline_american"].apply(american_to_decimal)
            ml_df["home_dk_decimal_moneyline"] = ml_df["home_dk_moneyline_american"].apply(american_to_decimal)

            ml_df["away_fair_decimal_moneyline"] = ml_df["away_prob"].apply(safe_inverse_probability)
            ml_df["home_fair_decimal_moneyline"] = ml_df["home_prob"].apply(safe_inverse_probability)

            ml_output = INPUT_DIR / f"{game_date}_{market}_moneyline.csv"
            ml_df.to_csv(ml_output, index=False)

            total_df = df.copy()

            total_df["dk_total_over_decimal"] = total_df["dk_total_over_american"].apply(american_to_decimal)
            total_df["dk_total_under_decimal"] = total_df["dk_total_under_american"].apply(american_to_decimal)

            fair_over = []
            fair_under = []

            for _, row in total_df.iterrows():
                lam = row["home_projected_goals"] + row["away_projected_goals"]
                T = row["total"]

                if pd.isna(T) or pd.isna(lam) or lam <= 0:
                    fair_over.append("")
                    fair_under.append("")
                    continue

                k = math.floor(T + POISSON_TOTAL_FLOOR_SHIFT)
                p_under = poisson_cdf(k, lam)
                p_over = 1 - p_under

                fair_under.append(1 / p_under if p_under > 0 else "")
                fair_over.append(1 / p_over if p_over > 0 else "")

            total_df["fair_total_over_decimal"] = fair_over
            total_df["fair_total_under_decimal"] = fair_under

            total_output = INPUT_DIR / f"{game_date}_{market}_total.csv"
            total_df.to_csv(total_output, index=False)

            pl_df = df.copy()

            pl_df["away_dk_puck_line_decimal"] = pl_df["away_dk_puck_line_american"].apply(american_to_decimal)
            pl_df["home_dk_puck_line_decimal"] = pl_df["home_dk_puck_line_american"].apply(american_to_decimal)

            pl_output = INPUT_DIR / f"{game_date}_{market}_puck_line.csv"
            pl_df.to_csv(pl_output, index=False)

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
