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

# ---------- JUICE LOOKUPS ----------

def band_lookup_odds(american_odds, fav_ud, venue, jt):
    r = jt[
        (jt.band_min <= american_odds) &
        (american_odds < jt.band_max) &
        (jt.fav_ud == fav_ud) &
        (jt.venue == venue)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def band_lookup_spread(spread_abs, fav_ud, venue, jt):
    r = jt[
        (jt.band_min <= spread_abs) &
        (spread_abs < jt.band_max) &
        (jt.fav_ud == fav_ud) &
        (jt.venue == venue)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def prob_bin_lookup(p, jt):
    r = jt[(jt.prob_bin_min <= p) & (p < jt.prob_bin_max)]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def spread_lookup(spread, jt):
    r = jt[jt.spread == spread]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def totals_side_lookup(side, jt):
    r = jt[jt.side == side]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

# ---------- MAIN ----------

def normalize_date(val):
    return str(val).replace("-", "_")

def run():
    JOBS = [
        # NBA ML — probability-based
        ("nba", "ml", "config/nba/nba_ml_juice.csv",
         "docs/win/nba/moneyline/ml_nba_*.csv",
         [
             ("home_ml_acceptable_american_odds", "home_team_moneyline_win_prob", "home"),
             ("away_ml_acceptable_american_odds", "away_team_moneyline_win_prob", "away"),
         ],
         "prob"),

        # NHL ML — NOW probability-based
        ("nhl", "ml", "config/nhl/nhl_ml_juice.csv",
         "docs/win/nhl/moneyline/ml_nhl_*.csv",
         [
             ("home_ml_acceptable_american_odds", "home_team_moneyline_win_prob", "home"),
             ("away_ml_acceptable_american_odds", "away_team_moneyline_win_prob", "away"),
         ],
         "prob"),

        # NCAAB ML — probability-based
        ("ncaab", "ml", "config/ncaab/ncaab_ml_juice.csv",
         "docs/win/ncaab/moneyline/ml_ncaab_*.csv",
         [
             ("home_ml_acceptable_american_odds", "home_team_moneyline_win_prob", "home"),
             ("away_ml_acceptable_american_odds", "away_team_moneyline_win_prob", "away"),
         ],
         "prob"),
    ]

    for league, market, juice_file, pattern, legs, mode in JOBS:
        jt = pd.read_csv(juice_file)
        out_dir = Path(f"docs/win/juice/{league}/{market}")
        out_dir.mkdir(parents=True, exist_ok=True)

        for f in glob.glob(pattern):
            df = pd.read_csv(f)
            game_date = normalize_date(df["date"].iloc[0])

            for odds_col, key_col, venue in legs:
                out_col = odds_col.replace("acceptable_american_odds", "juice_odds")

                def apply(row):
                    try:
                        american = row[odds_col]
                        base_dec = american_to_decimal(american)
                        d = base_dec * (1 + prob_bin_lookup(row[key_col], jt))
                        return decimal_to_american(d)
                    except Exception:
                        return american

                df[out_col] = df.apply(apply, axis=1)

            out = out_dir / f"juice_{league}_{market}_{game_date}.csv"
            df.to_csv(out, index=False)
            print(f"Wrote {out}")

if __name__ == "__main__":
    run()
