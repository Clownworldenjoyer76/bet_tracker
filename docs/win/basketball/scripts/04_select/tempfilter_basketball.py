#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/tempfilter_basketball.py

import pandas as pd
from pathlib import Path

SELECT_DIR = Path("docs/win/basketball/04_select")
OUTPUT_DIR = SELECT_DIR / "daily_slate"


def get_price(row, side):
    """
    Safely extract moneyline price
    """
    try:
        return float(row.get(side, 0) or 0)
    except:
        return 0


def get_spread(row, side):
    """
    Safely extract spread
    """
    try:
        return float(row.get(side, 0) or 0)
    except:
        return 0


def get_total(row):
    try:
        return float(row.get("total_line", 0) or 0)
    except:
        return 0


def allow_row(row):

    market = str(row.get("market", ""))
    market_type = str(row.get("market_type", ""))

    ####################################
    # NBA RULES
    ####################################

    if "NBA" in market:

        # Shut off NBA moneylines completely
        if market_type == "moneyline":
            return False

        if market_type == "spread":

            home = get_spread(row, "home_spread")
            away = get_spread(row, "away_spread")

            # avoid coin flip band
            if -3 <= home <= 3:
                return False

            # allowed stronger ranges
            if -15 <= home <= -7:
                return True

            if -15 <= away <= -7:
                return True

            if -7 <= away <= -1:
                return True

            # otherwise reject
            return False

        return True


    ####################################
    # NCAAB RULES
    ####################################

    if "NCAAB" in market:

        ####################################
        # MONEYLINE
        ####################################
        if market_type == "moneyline":

            home_ml = get_price(row, "home_moneyline")
            away_ml = get_price(row, "away_moneyline")

            # shut off expensive home ML
            if home_ml <= -200:
                return False

            # allow away ML favorites only
            if away_ml < 0:
                return True

            return False

        ####################################
        # SPREAD
        ####################################
        if market_type == "spread":

            home_spread = get_spread(row, "home_spread")
            away_spread = get_spread(row, "away_spread")

            # ban away dogs +1 to +7
            if 1 <= away_spread <= 7:
                return False

            # ban home short dogs
            if 1 <= home_spread <= 3:
                return False

            # ban home mid favorites
            if -10 <= home_spread <= -5:
                return False

            # prefer home -3 to -1
            if -3 <= home_spread <= -1:
                return True

            return True

        ####################################
        # TOTALS
        ####################################
        if market_type == "total":

            total = get_total(row)

            over_edge = float(row.get("over_edge_decimal", 0) or 0)
            under_edge = float(row.get("under_edge_decimal", 0) or 0)

            if under_edge > over_edge:
                # UNDER filters

                if total <= 140:
                    return False

                if total >= 155:
                    return False

                if 140 < total <= 150:
                    return True

                return False

            else:
                # OVER filters

                if total < 150:
                    return False

                if 150 <= total <= 160:
                    return True

                return False

    return True


def process_file(file):

    df = pd.read_csv(file)

    if df.empty:
        return

    filtered = df[df.apply(allow_row, axis=1)]

    filtered.to_csv(file, index=False)

    print(f"Filtered: {file.name}  ({len(df)} -> {len(filtered)})")


def main():

    files = list(OUTPUT_DIR.glob("*.csv"))

    if not files:
        print("No files found.")
        return

    for f in files:
        if f.name in ["nba_selected.csv", "ncaab_selected.csv"]:
            continue

        process_file(f)

    print("Temp filtering complete.")


if __name__ == "__main__":
    main()
