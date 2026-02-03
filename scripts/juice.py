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
        # NBA / NHL MONEYLINE (ODDS-BANDED)
        ("nba", "ml", "config/nba/nba_ml_juice.csv",
         "docs/win/nba/moneyline/ml_nba_*.csv",
         [
             ("home_ml_acceptable_american_odds", "home_team_moneyline_win_prob", "home"),
             ("away_ml_acceptable_american_odds", "away_team_moneyline_win_prob", "away"),
         ],
         "odds_band"),

        ("nhl", "ml", "config/nhl/nhl_ml_juice.csv",
         "docs/win/nhl/moneyline/ml_nhl_*.csv",
         [
             ("home_ml_acceptable_american_odds", "home_team_moneyline_win_prob", "home"),
             ("away_ml_acceptable_american_odds", "away_team_moneyline_win_prob", "away"),
         ],
         "odds_band"),

        # NCAAB MONEYLINE (PROBABILITY-BINNED)
        ("ncaab", "ml", "config/ncaab/ncaab_ml_juice.csv",
         "docs/win/ncaab/moneyline/ml_ncaab_*.csv",
         [
             ("home_ml_acceptable_american_odds", "home_team_moneyline_win_prob", "home"),
             ("away_ml_acceptable_american_odds", "away_team_moneyline_win_prob", "away"),
         ],
         "prob"),

        # NBA SPREADS (SPREAD-SIZE-BANDED)
        ("nba", "spreads", "config/nba/nba_spreads_juice.csv",
         "docs/win/nba/spreads/spreads_nba_*.csv",
         [
             ("home_spread_acceptable_american_odds", "home_spread", "home"),
             ("away_spread_acceptable_american_odds", "away_spread", "away"),
         ],
         "spread_band"),

        # NCAAB SPREADS
        ("ncaab", "spreads", "config/ncaab/ncaab_spreads_juice.csv",
         "docs/win/ncaab/spreads/spreads_ncaab_*.csv",
         [
             ("home_spread_acceptable_american_odds", "home_spread", None),
             ("away_spread_acceptable_american_odds", "away_spread", None),
         ],
         "spread"),

        # NHL SPREADS (unchanged)
        ("nhl", "spreads", "config/nhl/nhl_spreads_juice.csv",
         "docs/win/nhl/spreads/spreads_nhl_*.csv",
         [
             ("home_spread_acceptable_american_odds", "home_spread_probability", "home"),
             ("away_spread_acceptable_american_odds", "away_spread_probability", "away"),
         ],
         "odds_band"),

        # TOTALS
        ("nba", "totals", "config/nba/nba_totals_juice.csv",
         "docs/win/nba/totals/ou_nba_*.csv",
         [
             ("over_acceptable_american_odds", "over_probability", "over"),
             ("under_acceptable_american_odds", "under_probability", "under"),
         ],
         "side"),

        ("ncaab", "totals", "config/ncaab/ncaab_ou_juice.csv",
         "docs/win/ncaab/totals/ou_ncaab_*.csv",
         [
             ("over_acceptable_american_odds", "over_probability", "over"),
             ("under_acceptable_american_odds", "under_probability", "under"),
         ],
         "side"),

        ("nhl", "totals", "config/nhl/nhl_totals_juice.csv",
         "docs/win/nhl/totals/ou_nhl_*.csv",
         [
             ("over_acceptable_american_odds", "over_probability", "over"),
             ("under_acceptable_american_odds", "under_probability", "under"),
         ],
         "side"),
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
                        base_dec = american_to_decimal(row[odds_col])

                        if mode == "spread_band":
                            spread = row[key_col]
                            spread_abs = abs(spread)
                            fav_ud = "favorite" if spread < 0 else "underdog"
                            juice = band_lookup_spread(spread_abs, fav_ud, venue, jt)
                            d = base_dec * (1 + juice)

                        elif mode == "odds_band":
                            american = row[odds_col]
                            p = row[key_col]
                            fav_ud = "favorite" if p >= 0.5 else "underdog"
                            juice = band_lookup_odds(american, fav_ud, venue, jt)
                            d = base_dec * (1 + juice)

                        elif mode == "prob":
                            d = base_dec * (1 + prob_bin_lookup(row[key_col], jt))

                        elif mode == "spread":
                            d = base_dec * (1 + spread_lookup(row[key_col], jt))

                        else:
                            d = base_dec * (1 + totals_side_lookup(venue, jt))

                        return decimal_to_american(d)

                    except Exception:
                        return row[odds_col]

                df[out_col] = df.apply(apply, axis=1)

            out = out_dir / f"juice_{league}_{market}_{game_date}.csv"
            df.to_csv(out, index=False)
            print(f"Wrote {out}")

if __name__ == "__main__":
    run()
