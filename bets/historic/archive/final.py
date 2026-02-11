# scripts/final.py

import pandas as pd
import glob
import sys
import re
from pathlib import Path
import numpy as np

DK_BASE = "docs/win/manual/normalized"
JUICE_BASE = "docs/win/juice"
FINAL_BASE = "docs/win/final"

def american_to_decimal(x):
    if pd.isna(x):
        return np.nan
    x = float(x)
    return 1 + (x / 100) if x > 0 else 1 + (100 / abs(x))

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

def normalize_teams(m):
    if "away_team_x" in m.columns:
        m["away_team"] = m["away_team_x"]
        m["home_team"] = m["home_team_x"]
    return m

def normalize_spreads(m):
    for side in ["away", "home"]:
        for col in [f"{side}_spread", f"{side}_spread_x", f"{side}_spread_y"]:
            if col in m.columns:
                m[f"{side}_spread"] = m[col]
                break
        else:
            raise KeyError(f"{side}_spread not found")
    return m

def resolve_total_column(m):
    candidates = [
        c for c in m.columns
        if "total" in c.lower() and pd.api.types.is_numeric_dtype(m[c])
    ]
    if not candidates:
        raise KeyError("No numeric total column found after merge")
    m["total"] = m[candidates[0]]
    return m

def emit(df, market, side, line, dk_dec, juice_dec, league):
    return pd.DataFrame({
        "file_date": df["file_date"],
        "league": league,
        "market": market,
        "away_team": df["away_team"],
        "home_team": df["home_team"],
        "bet_side": side,
        "line": line,
        "dk_decimal_odds": dk_dec,
        "juice_decimal_odds": juice_dec,
    })

plays = []
dates = set()
leagues = ["nba", "ncaab", "nhl"]

for league in leagues:

    # ===== MONEYLINE =====
    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_moneyline_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/ml/juice_{league}_ml_*.csv")

    if dk is not None and juice is not None:
        m = normalize_teams(dk.merge(juice, on="game_id"))
        m["file_date"] = dk_date
        dates.update([dk_date, juice_date])

        for side in ["away", "home"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_ml_juice_odds"].apply(american_to_decimal)
            keep = dk_dec >= juice_dec

            plays.append(
                emit(m[keep], "ml", side, None,
                     dk_dec[keep], juice_dec[keep],
                     f"{league}_moneyline")
            )

    # ===== SPREADS =====
    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_spreads_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/spreads/juice_{league}_spreads_*.csv")

    if dk is not None and juice is not None:
        m = normalize_teams(dk.merge(juice, on="game_id"))
        m = normalize_spreads(m)
        m["file_date"] = dk_date
        dates.update([dk_date, juice_date])

        for side in ["away", "home"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_spread_juice_odds"].apply(american_to_decimal)
            line = m[f"{side}_spread"]
            keep = dk_dec >= juice_dec

            plays.append(
                emit(m[keep], "spreads", side, line[keep],
                     dk_dec[keep], juice_dec[keep],
                     f"{league}_spreads")
            )

    # ===== TOTALS =====
    dk, dk_date = load_latest(f"{DK_BASE}/dk_{league}_totals_*.csv")
    juice, juice_date = load_latest(f"{JUICE_BASE}/{league}/totals/juice_{league}_totals_*.csv")

    if dk is not None and juice is not None:
        m = normalize_teams(dk.merge(juice, on="game_id"))
        m = resolve_total_column(m)
        m["file_date"] = dk_date
        dates.update([dk_date, juice_date])

        for side in ["over", "under"]:
            dk_dec = m[f"{side}_decimal_odds"]
            juice_dec = m[f"{side}_juice_odds"].apply(american_to_decimal)
            line = m["total"]
            keep = dk_dec >= juice_dec

            plays.append(
                emit(m[keep], "totals", side, line[keep],
                     dk_dec[keep], juice_dec[keep],
                     f"{league}_totals")
            )

if not plays:
    print("No playable bets found.")
    sys.exit(0)

date = max(d for d in dates if d)
final_df = pd.concat(plays, ignore_index=True)

Path(FINAL_BASE).mkdir(parents=True, exist_ok=True)
final_df.to_csv(f"{FINAL_BASE}/plays_{date}.csv", index=False)

print(f"Plays written for {date}")
