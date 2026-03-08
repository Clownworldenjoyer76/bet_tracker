#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/tempfilter_basketball.py

import pandas as pd
from pathlib import Path

SELECT_DIR = Path("docs/win/basketball/04_select")
OUTPUT_DIR = SELECT_DIR / "daily_slate"


def get_price(row, side):
    try:
        return float(row.get(side, 0) or 0)
    except:
        return 0


def get_spread(row, side):
    try:
        return float(row.get(side, 0) or 0)
    except:
        return 0


def get_total(row):
    try:
        return float(row.get("total_line", 0) or 0)
    except:
        return 0


def get_projection_diff(row):
    try:
        proj = float(row.get("total_projected_points", 0) or 0)
        line = float(row.get("total_line", 0) or 0)
        return abs(proj - line)
    except:
        return 0


def allow_row(row):

    market = str(row.get("market", ""))
    market_type = str(row.get("market_type", ""))

    ####################################
    # NBA RULES
    ####################################

    if "NBA" in market:

        ####################################
        # MONEYLINE
        ####################################

        if market_type == "moneyline":

            home_edge = float(row.get("home_edge_decimal", 0) or 0)
            away_edge = float(row.get("away_edge_decimal", 0) or 0)

            home_ml = get_price(row, "home_moneyline")
            away_ml = get_price(row, "away_moneyline")

            # check home side
            if home_edge >= 0.06 and -180 <= home_ml <= 180:
                return True

            # check away side
            if away_edge >= 0.06 and -180 <= away_ml <= 180:
                return True

            return False

        ####################################
        # SPREAD
        ####################################

        if market_type == "spread":

            home_spread = get_spread(row, "home_spread")
            away_spread = get_spread(row, "away_spread")

            home_edge = float(row.get("home_edge_decimal", 0) or 0)
            away_edge = float(row.get("away_edge_decimal", 0) or 0)

            spread = home_spread if home_spread != 0 else away_spread
            edge = max(home_edge, away_edge)

            if edge < 0.07:
                return False

            if abs(spread) > 15:
                return False

            if -2 <= spread <= 2:
                return False

            return True

        ####################################
        # TOTALS
        ####################################

        if market_type == "total":

            total = get_total(row)
            proj_diff = get_projection_diff(row)

            home_spread = abs(get_spread(row, "home_spread"))
            away_spread = abs(get_spread(row, "away_spread"))
            spread = max(home_spread, away_spread)

            over_edge = float(row.get("over_edge_decimal", 0) or 0)
            under_edge = float(row.get("under_edge_decimal", 0) or 0)

            # total line limit
            if total > 245:
                return False

            # projection difference
            if proj_diff < 4:
                return False

            # skip large spread + large total
            if spread >= 12 and total >= 240:
                return False

            if under_edge > over_edge:

                # UNDER rules
                if total <= 205:
                    return False

                if under_edge < 0.06:
                    return False

                if under_edge > 0.35:
                    return False

                return True

            else:

                # OVER rules
                if total <= 205:
                    if over_edge < 0.04:
                        return False
                else:
                    if over_edge < 0.06:
                        return False

                if over_edge > 0.35:
                    return False

                return True

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

            if home_ml <= -200:
                return False

            if away_ml < 0:
                return True

            return False

        ####################################
        # SPREAD
        ####################################
        if market_type == "spread":

            home_spread = get_spread(row, "home_spread")
            away_spread = get_spread(row, "away_spread")

            if 1 <= away_spread <= 7:
                return False

            if 1 <= home_spread <= 3:
                return False

            if -10 <= home_spread <= -5:
                return False

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

                if total <= 140:
                    return False

                if total >= 155:
                    return False

                if 140 < total <= 150:
                    return True

                return False

            else:

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
