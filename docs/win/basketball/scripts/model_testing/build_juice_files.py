#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/build_juice_files.py

import pandas as pd
import glob
from pathlib import Path
from scipy.stats import norm, poisson

CONFIG = Path("docs/win/basketball/model_testing/rule_config.py")


def load_config():
    if not CONFIG.exists():
        return {}
    scope = {}
    exec(CONFIG.read_text(), {}, scope)
    return scope


CFG = load_config()

INPUT_DIR = Path("docs/win/basketball/01_merge")

NBA_TOTAL_STD = CFG.get("NBA_TOTAL_STD", 14)
NBA_SPREAD_STD = CFG.get("NBA_SPREAD_STD", 15)
NCAAB_TOTAL_STD = CFG.get("NCAAB_TOTAL_STD", 12)
NCAAB_SPREAD_STD = CFG.get("NCAAB_SPREAD_STD", 15)

NBA_TOTAL_EDGE = CFG.get("NBA_TOTAL_EDGE", 0.05)
NBA_SPREAD_EDGE = CFG.get("NBA_SPREAD_EDGE", 0.05)
NBA_ML_HOME_EDGE = CFG.get("NBA_ML_HOME_EDGE", 0.05)
NBA_ML_AWAY_EDGE = CFG.get("NBA_ML_AWAY_EDGE", 0.05)

NCAAB_TOTAL_EDGE = CFG.get("NCAAB_TOTAL_EDGE", 0.05)
NCAAB_SPREAD_EDGE = CFG.get("NCAAB_SPREAD_EDGE", 0.05)
NCAAB_ML_HOME_EDGE = CFG.get("NCAAB_ML_HOME_EDGE", 0.05)
NCAAB_ML_AWAY_EDGE = CFG.get("NCAAB_ML_AWAY_EDGE", 0.05)


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
        return f"+{int(round((dec - 1) * 100))}"
    return f"-{int(round(100 / (dec - 1)))}"


def clamp_probability(p):
    return min(max(p, 0.05), 0.95)


def main():

    files = glob.glob(str(INPUT_DIR / "basketball_*.csv"))

    for file_path in files:

        df = pd.read_csv(file_path)
        if df.empty:
            continue

        df["home_prob"] = pd.to_numeric(df["home_prob"], errors="coerce")
        df["away_prob"] = pd.to_numeric(df["away_prob"], errors="coerce")

        game_date = df["game_date"].iloc[0]
        market = df["market"].iloc[0]

        if market == "NBA":
            prob_sum = df["home_prob"] + df["away_prob"]
            df["home_prob"] = df["home_prob"] / prob_sum
            df["away_prob"] = df["away_prob"] / prob_sum
            total_std = NBA_TOTAL_STD
            spread_std = NBA_SPREAD_STD
            total_edge = NBA_TOTAL_EDGE
            spread_edge = NBA_SPREAD_EDGE
            home_ml_edge = NBA_ML_HOME_EDGE
            away_ml_edge = NBA_ML_AWAY_EDGE
        else:
            total_std = NCAAB_TOTAL_STD
            spread_std = NCAAB_SPREAD_STD
            total_edge = NCAAB_TOTAL_EDGE
            spread_edge = NCAAB_SPREAD_EDGE
            home_ml_edge = NCAAB_ML_HOME_EDGE
            away_ml_edge = NCAAB_ML_AWAY_EDGE

        ml = df.copy()

        ml["away_dk_decimal_moneyline"] = ml["away_dk_moneyline_american"].apply(american_to_decimal)
        ml["home_dk_decimal_moneyline"] = ml["home_dk_moneyline_american"].apply(american_to_decimal)

        ml["away_fair_decimal_moneyline"] = 1 / ml["away_prob"]
        ml["home_fair_decimal_moneyline"] = 1 / ml["home_prob"]

        ml["away_acceptable_decimal_moneyline"] = ml["away_fair_decimal_moneyline"] * (1 + away_ml_edge)
        ml["home_acceptable_decimal_moneyline"] = ml["home_fair_decimal_moneyline"] * (1 + home_ml_edge)

        ml["away_acceptable_american_moneyline"] = ml["away_acceptable_decimal_moneyline"].apply(to_american)
        ml["home_acceptable_american_moneyline"] = ml["home_acceptable_decimal_moneyline"].apply(to_american)

        ml.to_csv(INPUT_DIR / f"{game_date}_{market}_moneyline.csv", index=False)

        totals = df.copy()

        totals["dk_total_over_decimal"] = totals["dk_total_over_american"].apply(american_to_decimal)
        totals["dk_total_under_decimal"] = totals["dk_total_under_american"].apply(american_to_decimal)

        fair_over, fair_under, acc_over, acc_under = [], [], [], []

        for _, r in totals.iterrows():

            T = r["total"]
            mean = r["total_projected_points"]

            if pd.isna(T):
                fair_over.append("")
                fair_under.append("")
                acc_over.append("")
                acc_under.append("")
                continue

            if market == "NCAAB":
                p_under = poisson.cdf(T - 0.5, mean)
            else:
                z = (T - mean) / total_std
                p_under = norm.cdf(z)

            p_under = clamp_probability(p_under)
            p_over = 1 - p_under

            fair_under_dec = 1 / p_under
            fair_over_dec = 1 / p_over

            fair_under.append(fair_under_dec)
            fair_over.append(fair_over_dec)
            acc_under.append(fair_under_dec * (1 + total_edge))
            acc_over.append(fair_over_dec * (1 + total_edge))

        totals["fair_total_over_decimal"] = fair_over
        totals["fair_total_under_decimal"] = fair_under
        totals["acceptable_total_over_decimal"] = acc_over
        totals["acceptable_total_under_decimal"] = acc_under
        totals["acceptable_total_over_american"] = totals["acceptable_total_over_decimal"].apply(to_american)
        totals["acceptable_total_under_american"] = totals["acceptable_total_under_decimal"].apply(to_american)

        totals.to_csv(INPUT_DIR / f"{game_date}_{market}_total.csv", index=False)

        spreads = df.copy()

        spreads["away_dk_spread_decimal"] = spreads["away_dk_spread_american"].apply(american_to_decimal)
        spreads["home_dk_spread_decimal"] = spreads["home_dk_spread_american"].apply(american_to_decimal)

        fair_home, fair_away, acc_home, acc_away = [], [], [], []

        for _, r in spreads.iterrows():

            mean_margin = r["home_projected_points"] - r["away_projected_points"]

            try:
                home_line = float(r["home_spread"])
            except Exception:
                fair_home.append("")
                fair_away.append("")
                acc_home.append("")
                acc_away.append("")
                continue

            p_home = 1 - norm.cdf(-home_line, mean_margin, spread_std)
            p_home = clamp_probability(p_home)
            p_away = 1 - p_home

            fair_home_dec = 1 / p_home
            fair_away_dec = 1 / p_away

            fair_home.append(fair_home_dec)
            fair_away.append(fair_away_dec)
            acc_home.append(fair_home_dec * (1 + spread_edge))
            acc_away.append(fair_away_dec * (1 + spread_edge))

        spreads["home_fair_spread_decimal"] = fair_home
        spreads["away_fair_spread_decimal"] = fair_away
        spreads["home_acceptable_spread_decimal"] = acc_home
        spreads["away_acceptable_spread_decimal"] = acc_away
        spreads["home_acceptable_spread_american"] = spreads["home_acceptable_spread_decimal"].apply(to_american)
        spreads["away_acceptable_spread_american"] = spreads["away_acceptable_spread_decimal"].apply(to_american)

        spreads.to_csv(INPUT_DIR / f"{game_date}_{market}_spread.csv", index=False)


if __name__ == "__main__":
    main()
