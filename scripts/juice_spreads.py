import pandas as pd
import glob
from pathlib import Path
import math

# ---------- ODDS HELPERS ----------

def american_to_decimal(a):
    return 1 + (a / 100 if a > 0 else 100 / abs(a))

def decimal_to_american(d):
    if not math.isfinite(d) or d <= 1:
        raise ValueError("Invalid decimal odds")
    return int(round((d - 1) * 100)) if d >= 2 else int(round(-100 / (d - 1)))

# ---------- SPREAD JUICE LOOKUP ----------

def band_lookup_spread(spread_abs, fav_ud, venue, jt):
    r = jt[
        (jt.band_min <= spread_abs) &
        (spread_abs < jt.band_max) &
        (jt.fav_ud == fav_ud) &
        (jt.venue == venue)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

# ---------- MAIN ----------

def normalize_date(val):
    return str(val).replace("-", "_")

def apply_spread_juice(df, juice_table, league, out_dir):
    game_date = normalize_date(df["date"].iloc[0])

    def apply_away(row):
        try:
            spread = row["away_spread"]
            fav_ud = "favorite" if spread < 0 else "underdog"
            base_dec = american_to_decimal(row["away_spread_acceptable_american_odds"])
            juice = band_lookup_spread(abs(spread), fav_ud, "away", juice_table)
            return decimal_to_american(base_dec * (1 + juice))
        except Exception:
            return row["away_spread_acceptable_american_odds"]

    def apply_home(row):
        try:
            spread = row["home_spread"]
            fav_ud = "favorite" if spread < 0 else "underdog"
            base_dec = american_to_decimal(row["home_spread_acceptable_american_odds"])
            juice = band_lookup_spread(abs(spread), fav_ud, "home", juice_table)
            return decimal_to_american(base_dec * (1 + juice))
        except Exception:
            return row["home_spread_acceptable_american_odds"]

    df["away_spread_juice_odds"] = df.apply(apply_away, axis=1)
    df["home_spread_juice_odds"] = df.apply(apply_home, axis=1)

    out = out_dir / f"juice_{league}_spreads_{game_date}.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out}")

def run():
    # ---------- NBA ----------
    nba_juice = pd.read_csv("config/nba/nba_spreads_juice.csv")
    nba_out_dir = Path("docs/win/juice/nba/spreads")
    nba_out_dir.mkdir(parents=True, exist_ok=True)

    for f in glob.glob("docs/win/nba/spreads/spreads_nba_*.csv"):
        df = pd.read_csv(f)
        apply_spread_juice(df, nba_juice, "nba", nba_out_dir)

    # ---------- NCAAB ----------
    ncaab_juice = pd.read_csv("config/ncaab/ncaab_spreads_juice.csv")
    ncaab_out_dir = Path("docs/win/juice/ncaab/spreads")
    ncaab_out_dir.mkdir(parents=True, exist_ok=True)

    for f in glob.glob("docs/win/ncaab/spreads/spreads_ncaab_*.csv"):
        df = pd.read_csv(f)
        apply_spread_juice(df, ncaab_juice, "ncaab", ncaab_out_dir)

    # ---------- NHL ----------
    nhl_juice = pd.read_csv("config/nhl/nhl_spreads_juice.csv")
    nhl_out_dir = Path("docs/win/juice/nhl/spreads")
    nhl_out_dir.mkdir(parents=True, exist_ok=True)

    for f in glob.glob("docs/win/nhl/spreads/spreads_nhl_*.csv"):
        df = pd.read_csv(f)
        apply_spread_juice(df, nhl_juice, "nhl", nhl_out_dir)

if __name__ == "__main__":
    run()
