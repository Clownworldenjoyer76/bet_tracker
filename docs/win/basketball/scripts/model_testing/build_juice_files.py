#!/usr/bin/env python3
# docs/win/basketball/scripts/model_testing/build_juice_files.py

import glob
from pathlib import Path

import pandas as pd
from scipy.stats import norm, poisson

CONFIG = Path("docs/win/basketball/model_testing/rule_config.py")
INPUT_DIR = Path("docs/win/basketball/01_merge")


def load_config():
    if not CONFIG.exists():
        return {}
    scope = {}
    exec(CONFIG.read_text(), {}, scope)
    return scope


CFG = load_config()

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
        return 1 + (odds / 100.0)
    return 1 + (100.0 / abs(odds))


def to_american(dec):
    if pd.isna(dec) or dec <= 1:
        return ""
    if dec >= 2:
        return f"+{int(round((dec - 1) * 100))}"
    return f"-{int(round(100 / (dec - 1)))}"


def clamp_probability(prob):
    return min(max(float(prob), 0.05), 0.95)


def coerce_columns(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def annotate_config(df, market, total_std, spread_std, total_edge, spread_edge, home_ml_edge, away_ml_edge):
    df["config_market"] = market
    df["config_total_std"] = total_std
    df["config_spread_std"] = spread_std
    df["config_total_edge"] = total_edge
    df["config_spread_edge"] = spread_edge
    df["config_home_ml_edge"] = home_ml_edge
    df["config_away_ml_edge"] = away_ml_edge
    return df


def main():
    files = glob.glob(str(INPUT_DIR / "basketball_*.csv"))

    for file_path in files:
        df = pd.read_csv(file_path)
        if df.empty:
            continue

        df = coerce_columns(df, [
            "home_prob",
            "away_prob",
            "total",
            "total_projected_points",
            "home_projected_points",
            "away_projected_points",
            "away_dk_moneyline_american",
            "home_dk_moneyline_american",
            "dk_total_over_american",
            "dk_total_under_american",
            "away_dk_spread_american",
            "home_dk_spread_american",
            "away_spread",
            "home_spread",
        ])

        game_date = str(df["game_date"].iloc[0])
        market = str(df["market"].iloc[0])

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

        ml = annotate_config(df.copy(), market, total_std, spread_std, total_edge, spread_edge, home_ml_edge, away_ml_edge)
        ml["away_dk_decimal_moneyline"] = ml["away_dk_moneyline_american"].apply(american_to_decimal)
        ml["home_dk_decimal_moneyline"] = ml["home_dk_moneyline_american"].apply(american_to_decimal)
        ml["away_fair_decimal_moneyline"] = 1 / ml["away_prob"]
        ml["home_fair_decimal_moneyline"] = 1 / ml["home_prob"]
        ml["away_acceptable_decimal_moneyline"] = ml["away_fair_decimal_moneyline"] * (1 + away_ml_edge)
        ml["home_acceptable_decimal_moneyline"] = ml["home_fair_decimal_moneyline"] * (1 + home_ml_edge)
        ml["away_acceptable_american_moneyline"] = ml["away_acceptable_decimal_moneyline"].apply(to_american)
        ml["home_acceptable_american_moneyline"] = ml["home_acceptable_decimal_moneyline"].apply(to_american)
        ml.to_csv(INPUT_DIR / f"{game_date}_{market}_moneyline.csv", index=False)

        totals = annotate_config(df.copy(), market, total_std, spread_std, total_edge, spread_edge, home_ml_edge, away_ml_edge)
        totals["dk_total_over_decimal"] = totals["dk_total_over_american"].apply(american_to_decimal)
        totals["dk_total_under_decimal"] = totals["dk_total_under_american"].apply(american_to_decimal)

        fair_over, fair_under, acc_over, acc_under = [], [], [], []
        for _, row in totals.iterrows():
            total_line = row["total"]
            mean = row["total_projected_points"]

            if pd.isna(total_line) or pd.isna(mean):
                fair_over.append("")
                fair_under.append("")
                acc_over.append("")
                acc_under.append("")
                continue

            if market == "NCAAB":
                p_under = poisson.cdf(total_line - 0.5, mean)
            else:
                z = (total_line - mean) / total_std
                p_under = norm.cdf(z)

            p_under = clamp_probability(p_under)
            p_over = clamp_probability(1 - p_under)

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

        spreads = annotate_config(df.copy(), market, total_std, spread_std, total_edge, spread_edge, home_ml_edge, away_ml_edge)
        spreads["away_dk_spread_decimal"] = spreads["away_dk_spread_american"].apply(american_to_decimal)
        spreads["home_dk_spread_decimal"] = spreads["home_dk_spread_american"].apply(american_to_decimal)

        fair_home, fair_away, acc_home, acc_away = [], [], [], []
        for _, row in spreads.iterrows():
            mean_margin = row["home_projected_points"] - row["away_projected_points"]
            home_line = row["home_spread"]

            if pd.isna(mean_margin) or pd.isna(home_line):
                fair_home.append("")
                fair_away.append("")
                acc_home.append("")
                acc_away.append("")
                continue

            p_home = 1 - norm.cdf(-home_line, mean_margin, spread_std)
            p_home = clamp_probability(p_home)
            p_away = clamp_probability(1 - p_home)

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
