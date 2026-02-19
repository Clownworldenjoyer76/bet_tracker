#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
from datetime import datetime

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/soccer/01_merge")
OUTPUT_DIR = Path("docs/win/soccer/02_juice")

JUICE_MAP = {
    "epl": Path("config/soccer/epl/epl_1x2_juice.csv"),
    "la_liga": Path("config/soccer/la_liga/laliga_1x2_juice.csv"),
    "bundesliga": Path("config/soccer/bundesliga/bundesliga_1x2_juice.csv"),
    "ligue1": Path("config/soccer/ligue1/ligue1_juice.csv"),
    "serie_a": Path("config/soccer/serie_a/seriea_1x2_juice.csv"),
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def decimal_to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1:
        return ""
    if decimal_odds >= 2.0:
        return f"+{int(round((decimal_odds - 1) * 100))}"
    return f"-{int(round(100 / (decimal_odds - 1)))}"


def find_band(prob, juice_df):
    match = juice_df[
        (juice_df["band_min"] <= prob) &
        (prob < juice_df["band_max"])
    ]
    if match.empty:
        raise ValueError(f"No juice band found for probability {prob}")
    return match.iloc[0]


def process_side(df, side, juice_tables):
    prob_col = f"{side}_prob"

    df[f"{side}_fair_decimal"] = ""
    df[f"{side}_juice_band"] = ""
    df[f"{side}_extra_juice"] = ""
    df[f"{side}_adjusted_prob"] = ""
    df[f"{side}_adjusted_decimal"] = ""
    df[f"{side}_adjusted_american"] = ""

    for idx, row in df.iterrows():
        prob = row[prob_col]

        if pd.isna(prob) or prob <= 0 or prob >= 1:
            continue

        league = row["league"]
        juice_df = juice_tables[league]

        # Fair decimal
        fair_decimal = 1 / prob

        # Find band
        band_row = find_band(prob, juice_df)
        extra_juice = band_row["extra_juice"]
        band_label = f"{band_row['band_min']}-{band_row['band_max']}"

        # Apply juice
        adjusted_prob = prob + extra_juice
        if adjusted_prob >= 0.999:
            adjusted_prob = 0.999

        adjusted_decimal = 1 / adjusted_prob
        adjusted_american = decimal_to_american(adjusted_decimal)

        df.at[idx, f"{side}_fair_decimal"] = fair_decimal
        df.at[idx, f"{side}_juice_band"] = band_label
        df.at[idx, f"{side}_extra_juice"] = extra_juice
        df.at[idx, f"{side}_adjusted_prob"] = adjusted_prob
        df.at[idx, f"{side}_adjusted_decimal"] = adjusted_decimal
        df.at[idx, f"{side}_adjusted_american"] = adjusted_american

    return df


# =========================
# CORE
# =========================

def main():
    input_files = glob.glob(str(INPUT_DIR / "soccer_*.csv"))

    for file_path in input_files:
        input_path = Path(file_path)
        df = pd.read_csv(input_path)

        if "league" not in df.columns:
            raise ValueError("Input file missing 'league' column")

        # Load juice tables per league
        leagues = df["league"].unique()
        juice_tables = {}

        for league in leagues:
            if league not in JUICE_MAP:
                raise ValueError(f"No juice config mapped for league: {league}")
            juice_tables[league] = pd.read_csv(JUICE_MAP[league])

        # Process sides
        for side in ["home", "draw", "away"]:
            if f"{side}_prob" not in df.columns:
                raise ValueError(f"Missing column: {side}_prob")
            df = process_side(df, side, juice_tables)

        # Output
        output_path = OUTPUT_DIR / input_path.name
        df.to_csv(output_path, index=False)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
