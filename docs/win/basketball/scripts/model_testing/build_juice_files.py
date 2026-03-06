# docs/win/basketball/scripts/model_testing/build_juice_files.py
#!/usr/bin/env python3

import pandas as pd
import glob
import sys
from pathlib import Path
from scipy.stats import norm, poisson

# =========================
# CONFIG OVERRIDE
# =========================

CONFIG = Path("docs/win/basketball/model_testing/rule_config.py")

def load_config():
    if not CONFIG.exists():
        return {}
    scope = {}
    exec(CONFIG.read_text(), {}, scope)
    return scope

CFG = load_config()

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/01_merge")

# =========================
# DEFAULT CONSTANTS
# =========================

EDGE = 0.05
NBA_TOTAL_EDGE = 0.05

NBA_TOTAL_STD = 14
NBA_SPREAD_STD = 15

NCAAB_TOTAL_STD = 12
NCAAB_SPREAD_STD = 15

# =========================
# APPLY TEST OVERRIDES
# =========================

EDGE = CFG.get("EDGE", EDGE)
NBA_TOTAL_EDGE = CFG.get("NBA_TOTAL_EDGE", NBA_TOTAL_EDGE)

NBA_TOTAL_STD = CFG.get("NBA_TOTAL_STD", NBA_TOTAL_STD)
NBA_SPREAD_STD = CFG.get("NBA_SPREAD_STD", NBA_SPREAD_STD)

NCAAB_TOTAL_STD = CFG.get("NCAAB_TOTAL_STD", NCAAB_TOTAL_STD)
NCAAB_SPREAD_STD = CFG.get("NCAAB_SPREAD_STD", NCAAB_SPREAD_STD)

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

def to_american(dec):
    if pd.isna(dec) or dec <= 1:
        return ""
    if dec >= 2:
        return f"+{int((dec - 1) * 100)}"
    return f"-{int(100 / (dec - 1))}"

def clamp_probability(p):
    return min(max(p, 0.05), 0.95)

def get_stds(market):
    if market == "NBA":
        return NBA_TOTAL_STD, NBA_SPREAD_STD
    return NCAAB_TOTAL_STD, NCAAB_SPREAD_STD

# =========================
# MAIN
# =========================

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

        total_std, spread_std = get_stds(market)

        # =========================
        # MONEYLINE
        # =========================

        ml = df.copy()

        ml["away_dk_decimal_moneyline"] = ml["away_dk_moneyline_american"].apply(american_to_decimal)
        ml["home_dk_decimal_moneyline"] = ml["home_dk_moneyline_american"].apply(american_to_decimal)

        ml["away_fair_decimal_moneyline"] = 1 / ml["away_prob"]
        ml["home_fair_decimal_moneyline"] = 1 / ml["home_prob"]

        ml["away_acceptable_decimal_moneyline"] = ml["away_fair_decimal_moneyline"] * (1 + EDGE)
        ml["home_acceptable_decimal_moneyline"] = ml["home_fair_decimal_moneyline"] * (1 + EDGE)

        ml["away_acceptable_american_moneyline"] = ml["away_acceptable_decimal_moneyline"].apply(to_american)
        ml["home_acceptable_american_moneyline"] = ml["home_acceptable_decimal_moneyline"].apply(to_american)

        ml.to_csv(INPUT_DIR / f"{game_date}_{market}_moneyline.csv", index=False)

        # =========================
        # TOTALS
        # =========================

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

            edge_used = NBA_TOTAL_EDGE if market == "NBA" else EDGE

            acc_under.append(fair_under_dec * (1 + edge_used))
            acc_over.append(fair_over_dec * (1 + edge_used))

        totals["fair_total_over_decimal"] = fair_over
        totals["fair_total_under_decimal"] = fair_under
        totals["acceptable_total_over_decimal"] = acc_over
        totals["acceptable_total_under_decimal"] = acc_under

        totals.to_csv(INPUT_DIR / f"{game_date}_{market}_total.csv", index=False)

        # =========================
        # SPREAD
        # =========================

        spreads = df.copy()

        spreads["away_dk_spread_decimal"] = spreads["away_dk_spread_american"].apply(american_to_decimal)
        spreads["home_dk_spread_decimal"] = spreads["home_dk_spread_american"].apply(american_to_decimal)

        fair_home, fair_away, acc_home, acc_away = [], [], [], []

        for _, r in spreads.iterrows():

            mean_margin = r["home_projected_points"] - r["away_projected_points"]

            try:
                home_line = float(r["home_spread"])
            except:
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

            acc_home.append(fair_home_dec * (1 + EDGE))
            acc_away.append(fair_away_dec * (1 + EDGE))

        spreads["home_fair_spread_decimal"] = fair_home
        spreads["away_fair_spread_decimal"] = fair_away

        spreads["home_acceptable_spread_decimal"] = acc_home
        spreads["away_acceptable_spread_decimal"] = acc_away

        spreads.to_csv(INPUT_DIR / f"{game_date}_{market}_spread.csv", index=False)

if __name__ == "__main__":
    main()
