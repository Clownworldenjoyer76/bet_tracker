# scripts/juice_ou.py

import pandas as pd
import glob
from pathlib import Path
import math

# ---------- ODDS HELPERS ----------

def american_to_decimal(a):
    return 1 + (a / 100 if a > 0 else 100 / abs(a))

def decimal_to_american(d):
    if not math.isfinite(d) or d <= 1:
        return ""
    return int(round((d - 1) * 100)) if d >= 2 else int(round(-100 / (d - 1)))

# ---------- JUICE LOOKUPS ----------

def band_lookup_total(total, side, jt):
    r = jt[
        (jt.band_min <= total) &
        (total < jt.band_max) &
        (jt.side == side)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def exact_lookup_total(total, side, jt):
    r = jt[
        (jt.over_under == total) &
        (jt.side == side)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

# ---------- MAIN ----------

def normalize_date(val):
    return str(val).replace("-", "_")

def run():
    JOBS = [
        # NBA totals (banded)
        (
            "nba",
            "docs/win/nba/totals/ou_nba_*.csv",
            "config/nba/nba_totals_juice.csv",
            "band"
        ),

        # NCAAB totals (exact match)
        (
            "ncaab",
            "docs/win/ncaab/totals/ou_ncaab_*.csv",
            "config/ncaab/ncaab_ou_juice.csv",
            "exact"
        ),

        # NHL totals (banded)
        (
            "nhl",
            "docs/win/nhl/totals/ou_nhl_*.csv",
            "config/nhl/nhl_totals_juice.csv",
            "band"
        ),
    ]

    for league, pattern, juice_file, mode in JOBS:
        jt = pd.read_csv(juice_file)

        out_dir = Path(f"docs/win/juice/{league}/totals")
        out_dir.mkdir(parents=True, exist_ok=True)

        for f in glob.glob(pattern):
            df = pd.read_csv(f)
            game_date = normalize_date(df["date"].iloc[0])

            def apply_over(row):
                try:
                    base_dec = american_to_decimal(row["over_acceptable_american_odds"])
                    if mode == "band":
                        juice = band_lookup_total(row["total"], "over", jt)
                    else:
                        juice = exact_lookup_total(row["total"], "over", jt)
                    return decimal_to_american(base_dec * (1 + juice))
                except Exception:
                    return ""

            def apply_under(row):
                try:
                    base_dec = american_to_decimal(row["under_acceptable_american_odds"])
                    if mode == "band":
                        juice = band_lookup_total(row["total"], "under", jt)
                    else:
                        juice = exact_lookup_total(row["total"], "under", jt)
                    return decimal_to_american(base_dec * (1 + juice))
                except Exception:
                    return ""

            df["over_juice_odds"] = df.apply(apply_over, axis=1)
            df["under_juice_odds"] = df.apply(apply_under, axis=1)

            out = out_dir / f"juice_{league}_totals_{game_date}.csv"
            df.to_csv(out, index=False)
            print(f"Wrote {out}")

if __name__ == "__main__":
    run()
