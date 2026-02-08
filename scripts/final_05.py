import pandas as pd
import glob
from pathlib import Path
import math

BASE = Path("docs/win/final/step_2")


# ---------- ODDS CONVERSION ----------

def american_to_decimal(a):
    """
    Convert American odds to decimal odds.
    Returns NaN for invalid / missing values.
    """
    try:
        a = float(a)
        if not math.isfinite(a) or a == 0:
            return pd.NA
        return 1 + (a / 100 if a > 0 else 100 / abs(a))
    except Exception:
        return pd.NA


def apply_decimal_columns(files, mapping):
    for f in files:
        df = pd.read_csv(f)

        added = 0
        for src_col, out_col in mapping.items():
            if src_col not in df.columns:
                print(f"Skipping column {src_col} in {f}")
                continue

            df[out_col] = df[src_col].apply(american_to_decimal)
            added += 1

        df.to_csv(f, index=False)
        print(f"Updated {f} | decimal cols added: {added}")


def run():
    # ---------- MONEYLINE ----------
    apply_decimal_columns(
        glob.glob(str(BASE / "*/ml/juice_*_ml_*.csv")),
        {
            "home_ml_juice_odds": "deci_home_ml_juice_odds",
            "away_ml_juice_odds": "deci_away_ml_juice_odds",
            "dk_away_odds": "deci_dk_away_odds",
            "dk_home_odds": "deci_dk_home_odds",
        },
    )

    # ---------- SPREADS ----------
    apply_decimal_columns(
        glob.glob(str(BASE / "*/spreads/juice_*_spreads_*.csv")),
        {
            "away_spread_juice_odds": "deci_away_spread_juice_odds",
            "home_spread_juice_odds": "deci_home_spread_juice_odds",
            "dk_away_odds": "deci_dk_away_odds",
            "dk_home_odds": "deci_dk_home_odds",
        },
    )

    # ---------- TOTALS ----------
    apply_decimal_columns(
        glob.glob(str(BASE / "*/totals/juice_*_totals_*.csv")),
        {
            "over_juice_odds": "deci_over_juice_odds",
            "under_juice_odds": "deci_under_juice_odds",
            "dk_over_odds": "deci_dk_over_odds",
            "dk_under_odds": "deci_dk_under_odds",
        },
    )


if __name__ == "__main__":
    run()
