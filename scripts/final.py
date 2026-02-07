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
    files = sorted(glob.glob(pattern))
    if not files:
        return None, None
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    date = max(extract_date(f) for f in files if extract_date(f))
    return df, date

def emit(df, market, side, line_val, dk_dec, juice_dec, league):
    out = pd.DataFrame({
        "file_date": df["file_date"],
        "league": league,
        "market": market,
        "away_team": df["away_team"],
        "home_team": df["home_team"],
        "bet_side": side,
        "line": line_val,
        "dk_decimal_odds": dk_dec,
        "juice_decimal_odds": juice_dec,
    })
    out["edge_decimal_diff"] = out["juice_decimal_odds"] - out["dk_decimal_odds"]
    return out

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
        m = dk.merge(juice, on="game_id")

        if "away_team_x" in m.columns:
            m["away_team"] = m["away_team_x"]
            m["home_team"] = m["home_team_x"]

        m["file_date"] = dk_date

        for side in ["away", "home"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_ml_juice_odds"].apply(american_to_decimal)

            out = emit(
                m,
                market="ml",
                side=side,
                line_val=None,
                dk_dec=dk_dec,
                juice_dec=juice_dec,
                league=f"{league}_moneyline",
            )

            edges.append(out[out.edge_decimal_diff > TOLERANCE])
            near.append(out[(out.edge_decimal_diff > 0) & (out.edge_decimal_diff <= NEAR_MISS_MAX)])

    # ================= SPREADS =================

    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_spreads_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")

    if dk is not None and juice is not None:
        dates.update([dk_date, juice_date])
        m = dk.merge(juice, on="game_id")

        if "away_team_x" in m.columns:
            m["away_team"] = m["away_team_x"]
            m["home_team"] = m["home_team_x"]

        # 🔑 normalize spread column
        if "spread" in m.columns:
            m["line"] = m["spread"]
        elif "line" in m.columns:
            m["line"] = m["line"]
        else:
            raise KeyError("No spread/line column found in DK spreads file")

        m["file_date"] = dk_date

        for side in ["away", "home"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_spread_juice_odds"].apply(american_to_decimal)

            out = emit(
                m,
                market="spreads",
                side=side,
                line_val=m["line"],
                dk_dec=dk_dec,
                juice_dec=juice_dec,
                league=f"{league}_spreads",
            )

            edges.append(out[out.edge_decimal_diff > TOLERANCE])
            near.append(out[(out.edge_decimal_diff > 0) & (out.edge_decimal_diff <= NEAR_MISS_MAX)])

    # ================= TOTALS =================

    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_totals_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/totals/juice_{league}_totals_*.csv")

    if dk is not None and juice is not None:
        dates.update([dk_date, juice_date])
        m = dk.merge(juice, on="game_id")

        if "away_team_x" in m.columns:
            m["away_team"] = m["away_team_x"]
            m["home_team"] = m["home_team_x"]

        m["file_date"] = dk_date

        for side in ["over", "under"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_juice_odds"].apply(american_to_decimal)

            out = emit(
                m,
                market="totals",
                side=side,
                line_val=m["total"],
                dk_dec=dk_dec,
                juice_dec=juice_dec,
                league=f"{league}_totals",
            )

            edges.append(out[out.edge_decimal_diff > TOLERANCE])
            near.append(out[(out.edge_decimal_diff > 0) & (out.edge_decimal_diff <= NEAR_MISS_MAX)])

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

print(f"Edges written for {date}")
if DEBUG:
    print(f"Edges: {len(final_df)} | Near misses: {len(near_df)}")
