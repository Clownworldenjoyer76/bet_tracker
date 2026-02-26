# docs/win/hockey/scripts/02_juice/apply_moneyline_juice.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
from datetime import datetime
import traceback
import sys

INPUT_DIR = Path("docs/win/hockey/01_merge")
OUTPUT_DIR = Path("docs/win/hockey/02_juice")
JUICE_FILE = Path("config/hockey/nhl/nhl_moneyline_juice.csv")

ERROR_DIR = Path("docs/win/hockey/errors/02_juice")
LOG_FILE = ERROR_DIR / "apply_moneyline_juice.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def american_to_decimal(odds):
    if pd.isna(odds):
        return None
    odds = float(odds)
    if odds > 0:
        return 1 + (odds / 100)
    return 1 + (100 / abs(odds))


def find_juice_row(juice_df, american, fav_ud, venue):
    band = juice_df[
        (juice_df["band_min"] <= american) &
        (american <= juice_df["band_max"]) &
        (juice_df["fav_ud"] == fav_ud) &
        (juice_df["venue"] == venue)
    ]
    if band.empty:
        raise ValueError(f"No juice band for {american}, {fav_ud}, {venue}")
    return band.iloc[0]["extra_juice"]


def apply_side(df, side, juice_df):
    american_col = f"{side}_dk_moneyline_american"
    fair_col = f"{side}_fair_decimal_moneyline"

    df[f"{side}_juiced_prob_moneyline"] = pd.NA

    for idx, row in df.iterrows():
        american = float(row[american_col])
        fair_decimal = float(row[fair_col])

        fav_ud = "favorite" if american < 0 else "underdog"
        venue = side

        extra_juice = find_juice_row(juice_df, american, fav_ud, venue)

        fair_prob = 1 / fair_decimal
        juiced_prob = fair_prob + extra_juice

        df.at[idx, f"{side}_juiced_prob_moneyline"] = juiced_prob

    return df


def normalize_probs_and_compute_decimal(df):
    for idx, row in df.iterrows():

        home_prob = float(row["home_juiced_prob_moneyline"])
        away_prob = float(row["away_juiced_prob_moneyline"])

        total = home_prob + away_prob

        if total <= 0:
            continue

        home_prob_norm = home_prob / total
        away_prob_norm = away_prob / total

        df.at[idx, "home_juiced_prob_moneyline"] = home_prob_norm
        df.at[idx, "away_juiced_prob_moneyline"] = away_prob_norm

        df.at[idx, "home_juiced_decimal_moneyline"] = 1 / home_prob_norm
        df.at[idx, "away_juiced_decimal_moneyline"] = 1 / away_prob_norm

    return df


def main():
    with open(LOG_FILE, "w") as log:
        log.write(f"=== APPLY MONEYLINE JUICE {datetime.utcnow().isoformat()}Z ===\n\n")

    try:
        juice_df = pd.read_csv(JUICE_FILE)
        files = glob.glob(str(INPUT_DIR / "*_NHL_moneyline.csv"))

        for file_path in files:
            df = pd.read_csv(file_path)

            df = apply_side(df, "home", juice_df)
            df = apply_side(df, "away", juice_df)

            # FIX: normalize both sides so probabilities sum to 1
            df = normalize_probs_and_compute_decimal(df)

            output_path = OUTPUT_DIR / Path(file_path).name
            df.to_csv(output_path, index=False)

            with open(LOG_FILE, "a") as log:
                log.write(f"Wrote {output_path}\n")

    except Exception as e:
        with open(LOG_FILE, "a") as log:
            log.write("\nERROR\n")
            log.write(str(e) + "\n")
            log.write(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
