import pandas as pd
import glob
from pathlib import Path
from datetime import datetime

# ---------- ODDS HELPERS ----------

def american_to_decimal(a):
    if a > 0:
        return 1 + a / 100
    return 1 + 100 / abs(a)

def decimal_to_american(d):
    if d >= 2:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))

# ---------- LOOKUPS ----------

def lookup_band_juice(row, jt):
    r = jt[
        (jt.band_min <= row.win_prob) &
        (row.win_prob < jt.band_max) &
        (jt.fav_ud == row.fav_ud) &
        (jt.venue == row.venue)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def lookup_prob_bin_juice(row, jt):
    r = jt[
        (jt.prob_bin_min <= row.win_prob) &
        (row.win_prob < jt.prob_bin_max)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def lookup_spread_juice(row, jt):
    r = jt[jt.spread == row.spread]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

def lookup_totals_side_juice(row, jt):
    r = jt[
        (jt.side == row.side) &
        (jt.over_under == row.over_under)
    ]
    return float(r.iloc[0].extra_juice) if not r.empty else 0.0

# ---------- CONFIG ----------

CONFIG = {
    "nba": {
        "ml": {
            "juice": "config/nba/nba_ml_juice.csv",
            "glob": "docs/win/nba/moneyline/ml_nba_*.csv",
            "lookup": lookup_band_juice,
            "cols": {
                "home_ml_acceptable_american_odd": "home_ml_juice_odds",
                "away_ml_acceptable_american_odds": "away_ml_juice_odds",
            },
        },
        "spreads": {
            "juice": "config/nba/nba_spreads_juice.csv",
            "glob": "docs/win/nba/spreads/spreads_nba_*.csv",
            "lookup": lookup_band_juice,
            "cols": {
                "home_spread_acceptable_american_odds": "home_spread_juice_odds",
                "away_spread_acceptable_american_odds": "away_spread_juice_odds",
            },
        },
        "totals": {
            "juice": "config/nba/nba_totals_juice.csv",
            "glob": "docs/win/nba/totals/ou_nba_*.csv",
            "lookup": lookup_totals_side_juice,
            "cols": {
                "over_acceptable_american_odds": "over_juice_odds",
                "under_acceptable_american_odds": "under_juice_odds",
            },
        },
    },
    "ncaab": {
        "ml": {
            "juice": "config/ncaab/ncaab_ml_juice.csv",
            "glob": "docs/win/ncaab/moneyline/ml_ncaab_*.csv",
            "lookup": lookup_prob_bin_juice,
            "cols": {
                "home_ml_acceptable_american_odd": "home_ml_juice_odds",
                "away_ml_acceptable_american_odds": "away_ml_juice_odds",
            },
        },
        "spreads": {
            "juice": "config/ncaab/ncaab_spreads_juice.csv",
            "glob": "docs/win/ncaab/spreads/spreads_ncaab_*.csv",
            "lookup": lookup_spread_juice,
            "cols": {
                "home_spread_acceptable_american_odds": "home_spread_juice_odds",
                "away_spread_acceptable_american_odds": "away_spread_juice_odds",
            },
        },
        "totals": {
            "juice": "config/ncaab/ncaab_ou_juice.csv",
            "glob": "docs/win/ncaab/totals/ou_ncaab_*.csv",
            "lookup": lookup_totals_side_juice,
            "cols": {
                "over_acceptable_american_odds": "over_juice_odds",
                "under_acceptable_american_odds": "under_juice_odds",
            },
        },
    },
    "nhl": {
        "ml": {
            "juice": "config/nhl/nhl_ml_juice.csv",
            "glob": "docs/win/nhl/moneyline/ml_nhl_*.csv",
            "lookup": lookup_band_juice,
            "cols": {
                "home_ml_acceptable_american_odd": "home_ml_juice_odds",
                "away_ml_acceptable_american_odds": "away_ml_juice_odds",
            },
        },
        "spreads": {
            "juice": "config/nhl/nhl_spreads_juice.csv",
            "glob": "docs/win/nhl/spreads/spreads_nhl_*.csv",
            "lookup": lookup_band_juice,
            "cols": {
                "home_spread_acceptable_american_odds": "home_spread_juice_odds",
                "away_spread_acceptable_american_odds": "away_spread_juice_odds",
            },
        },
        "totals": {
            "juice": "config/nhl/nhl_totals_juice.csv",
            "glob": "docs/win/nhl/totals/ou_nhl_*.csv",
            "lookup": lookup_totals_side_juice,
            "cols": {
                "over_acceptable_american_odds": "over_juice_odds",
                "under_acceptable_american_odds": "under_juice_odds",
            },
        },
    },
}

# ---------- MAIN ----------

def run():
    today = datetime.utcnow().strftime("%Y%m%d")

    for league, markets in CONFIG.items():
        for market, cfg in markets.items():
            jt = pd.read_csv(cfg["juice"])
            files = glob.glob(cfg["glob"])

            out_dir = Path(f"docs/win/juice/{league}/{market}")
            out_dir.mkdir(parents=True, exist_ok=True)

            for f in files:
                df = pd.read_csv(f)

                for src, dst in cfg["cols"].items():
                    def apply(row):
                        base = american_to_decimal(row[src])
                        juice = cfg["lookup"](row, jt)
                        return decimal_to_american(base * (1 + juice))

                    df[dst] = df.apply(apply, axis=1)

                out = out_dir / f"juice_{league}_{market}_{today}.csv"
                df.to_csv(out, index=False)
                print(f"Wrote {out}")

if __name__ == "__main__":
    run()
