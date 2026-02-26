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


def main():
    with open(LOG_FILE, "w") as log:
        log.write(f"=== APPLY MONEYLINE JUICE {datetime.utcnow().isoformat()}Z ===\n\n")

    try:
        juice_df = pd.read_csv(JUICE_FILE)
        files = glob.glob(str(INPUT_DIR / "*_NHL_moneyline.csv"))

        for file_path in files:
            df = pd.read_csv(file_path)

            df["home_juiced_decimal_moneyline"] = pd.NA
            df["away_juiced_decimal_moneyline"] = pd.NA

            for idx, row in df.iterrows():

                # ---- HOME ----
                home_american = float(row["home_dk_moneyline_american"])
                home_fair_decimal = float(row["home_fair_decimal_moneyline"])

                home_fav_ud = "favorite" if home_american < 0 else "underdog"
                home_extra = find_juice_row(juice_df, home_american, home_fav_ud, "home")

                # Apply juice directly to decimal
                home_juiced_decimal = home_fair_decimal + home_extra
                if home_juiced_decimal <= 1.001:
                    home_juiced_decimal = 1.001

                df.at[idx, "home_juiced_decimal_moneyline"] = home_juiced_decimal

                # ---- AWAY ----
                away_american = float(row["away_dk_moneyline_american"])
                away_fair_decimal = float(row["away_fair_decimal_moneyline"])

                away_fav_ud = "favorite" if away_american < 0 else "underdog"
                away_extra = find_juice_row(juice_df, away_american, away_fav_ud, "away")

                away_juiced_decimal = away_fair_decimal + away_extra
                if away_juiced_decimal <= 1.001:
                    away_juiced_decimal = 1.001

                df.at[idx, "away_juiced_decimal_moneyline"] = away_juiced_decimal

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
