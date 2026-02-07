# scripts/final.py

import pandas as pd
import glob
import sys
import re
from pathlib import Path

# ================= CONFIG =================

TOLERANCE = 0.005
NEAR_MISS_MAX = TOLERANCE

DK_BASE = "docs/win/manual/normalized"
JUICE_BASE = "docs/win/juice"
FINAL_BASE = "docs/win/final"

DEBUG = "--debug" in sys.argv

# ================= HELPERS =================

def log(msg):
    if DEBUG:
        print(msg)

def american_to_decimal(odds):
    if pd.isna(odds):
        return None
    odds = float(odds)
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))

def extract_date(path):
    m = re.search(r"(\d{4}_\d{2}_\d{2})", path)
    return m.group(1) if m else None

def load_latest(pattern):
    files = glob.glob(pattern)
    if not files:
        return None, None
    files.sort()
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    date = max(extract_date(f) for f in files)
    return df, date

def normalize_identity(df):
    """
    DK normalized files are the single source of truth
    for league / team identity columns.
    """
    df["league"] = df["league_dk"]
    df["away_team"] = df["away_team_dk"]
    df["home_team"] = df["home_team_dk"]
    return df

def emit(df, market, side, line_col, dk_dec, juice_dec):
    df = df.copy()
    df["market"] = market
    df["bet_side"] = side
    df["line"] = df[line_col] if line_col else None
    df["dk_decimal_odds"] = dk_dec
    df["juice_decimal_odds"] = juice_dec
    df["edge_decimal_diff"] = juice_dec - dk_dec
    return df

def select_cols(df):
    return df[
        [
            "file_date",
            "league",
            "market",
            "away_team",
            "home_team",
            "bet_side",
            "line",
            "dk_decimal_odds",
            "juice_decimal_odds",
            "edge_decimal_diff",
        ]
    ]

# ================= MAIN =================

edges = []
near = []
dates = set()

leagues = ["nba", "ncaab", "nhl"]

for league in leagues:

    # ================= MONEYLINE =================

    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_moneyline_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/ml/juice_{league}_ml_*.csv")

    if dk is not None and juice is not None:
        dates.update([dk_date, juice_date])

        m = dk.merge(juice, on="game_id", suffixes=("_dk", "_j"))
        m = normalize_identity(m)

        for side in ["away", "home"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_ml_juice_odds"].apply(american_to_decimal)

            out = emit(
                m,
                "ml",
                side,
                None,
                dk_dec,
                juice_dec,
            )

            out["file_date"] = dk_date

            edges.append(select_cols(out[out.edge_decimal_diff > TOLERANCE]))
            near.append(
                select_cols(
                    out[
                        (out.edge_decimal_diff > 0)
                        & (out.edge_decimal_diff <= NEAR_MISS_MAX)
                    ]
                )
            )

    # ================= SPREADS =================

    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_spreads_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")

    if dk is not None and juice is not None:
        dates.update([dk_date, juice_date])

        m = dk.merge(juice, on="game_id", suffixes=("_dk", "_j"))
        m = normalize_identity(m)

        for side in ["away", "home"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_spread_juice_odds"].apply(american_to_decimal)

            out = emit(
                m,
                "spreads",
                side,
                f"{side}_spread",
                dk_dec,
                juice_dec,
            )

            out["file_date"] = dk_date

            edges.append(select_cols(out[out.edge_decimal_diff > TOLERANCE]))
            near.append(
                select_cols(
                    out[
                        (out.edge_decimal_diff > 0)
                        & (out.edge_decimal_diff <= NEAR_MISS_MAX)
                    ]
                )
            )

    # ================= TOTALS =================

    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_totals_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/totals/juice_{league}_totals_*.csv")

    if dk is not None and juice is not None:
        dates.update([dk_date, juice_date])

        m = dk.merge(juice, on="game_id", suffixes=("_dk", "_j"))
        m = normalize_identity(m)

        for side in ["over", "under"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_juice_odds"].apply(american_to_decimal)

            out = emit(
                m,
                "totals",
                side,
                "total",
                dk_dec,
                juice_dec,
            )

            out["file_date"] = dk_date

            edges.append(select_cols(out[out.edge_decimal_diff > TOLERANCE]))
            near.append(
                select_cols(
                    out[
                        (out.edge_decimal_diff > 0)
                        & (out.edge_decimal_diff <= NEAR_MISS_MAX)
                    ]
                )
            )

# ================= WRITE OUTPUT =================

if not edges and not near:
    print("No edges or near misses found.")
    sys.exit(0)

date = max(d for d in dates if d)

final_df = pd.concat(edges, ignore_index=True)
near_df = pd.concat(near, ignore_index=True)

Path(FINAL_BASE).mkdir(parents=True, exist_ok=True)

final_df.to_csv(f"{FINAL_BASE}/edges_{date}.csv", index=False)
near_df.to_csv(f"{FINAL_BASE}/near_miss_{date}.csv", index=False)

for lg in final_df["league"].unique():
    out_dir = Path(f"{FINAL_BASE}/{lg}")
    out_dir.mkdir(parents=True, exist_ok=True)
    final_df[final_df.league == lg].to_csv(
        out_dir / f"edges_{lg}_{date}.csv",
        index=False,
    )

print(f"Edges written for {date}")
if DEBUG:
    print(f"Edges: {len(final_df)} | Near misses: {len(near_df)}")
