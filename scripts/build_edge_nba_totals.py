#!/usr/bin/env python3
"""
Build NBA Totals Evaluation File
Source: Model (total_points) + Manual DK Normalized (total)
"""

import pandas as pd
import glob
from math import sqrt, erf
from pathlib import Path
from datetime import datetime

# -----------------------------
# PATHS
# -----------------------------
EDGE_DIR = Path("docs/win/edge")
DK_NORM_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nba/totals")
CONFIG_PATH = Path("config/nba/nba_juice_table.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MIN_LAM = 150.0
MAX_LAM = 300.0

# -----------------------------
# HELPERS
# -----------------------------
def force_half_point(x: float) -> float:
    rounded = round(x * 2) / 2
    if rounded.is_integer():
        return rounded + 0.5
    return rounded

def normal_cdf(x: float, mu: float, sigma: float) -> float:
    z = (x - mu) / (sigma * sqrt(2))
    return 0.5 * (1 + erf(z))

def fair_decimal(p: float) -> float:
    return 1.0 / p if p > 0 else 0.0

def decimal_to_american(d: float) -> int:
    if d <= 1.0: return 0
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))

def acceptable_decimal(p: float, edge_pct: float) -> float:
    return (1.0 / p) * (1.0 + edge_pct) if p > 0 else 0.0

# -----------------------------
# LOAD JUICE CONFIG
# -----------------------------
def load_totals_juice_rules():
    rules = []
    if not CONFIG_PATH.exists():
        return rules
    
    df_juice = pd.read_csv(CONFIG_PATH)
    df_juice = df_juice[df_juice["market_type"] == "totals"]
    
    for _, row in df_juice.iterrows():
        rules.append({
            "low": float(row["band_low"]),
            "high": float(row["band_high"]),
            "side": str(row["side"]).lower(),
            "extra": float(row["extra_juice_pct"]),
        })
    return rules

TOTALS_JUICE_RULES = load_totals_juice_rules()

def lookup_totals_juice(market_total: float, side: str) -> float:
    for rule in TOTALS_JUICE_RULES:
        if rule["low"] <= market_total <= rule["high"]:
            if rule["side"] == "any" or rule["side"] == side.lower():
                return rule["extra"]
    return 0.0

# -----------------------------
# MAIN
# -----------------------------
def main():
    # 1. Load Latest Model Predictions
    model_files = sorted(glob.glob(str(EDGE_DIR / "edge_nba_*.csv")))
    if not model_files:
        raise FileNotFoundError("No NBA edge files found in docs/win/edge")
    df_model = pd.read_csv(model_files[-1])

    # 2. Load Latest Normalized DK Totals
    dk_files = sorted(glob.glob(str(DK_NORM_DIR / "norm_dk_nba_totals_*.csv")))
    if not dk_files:
        raise FileNotFoundError("No DK norm files found in docs/win/manual/normalized")
    df_dk = pd.read_csv(dk_files[-1])

    # 3. Merge on Team Name
    # We only need the 'team' and 'total' columns from the DK file
    df_dk_subset = df_dk[['team', 'total']].copy()
    df_dk_subset.rename(columns={'total': 'dk_market_total'}, inplace=True)
    
    # Merge model predictions with manual market totals
    df = pd.merge(df_model, df_dk_subset, on='team', how='inner')

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_nba_totals_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    results = []

    for _, row in df.iterrows():
        game_id = row.get("game_id", "N/A")
        team_1 = row.get("team", "")
        team_2 = row.get("opponent", "")
        
        try:
            lam = float(row["total_points"])
            # Use 'dk_market_total' from the merged manual file
            raw_market_total = float(row["dk_market_total"])
        except (ValueError, TypeError, KeyError):
            continue

        side = "NO PLAY"
        p_selected = None
        market_total = None

        if MIN_LAM <= lam <= MAX_LAM:
            market_total = force_half_point(raw_market_total)
            sigma = sqrt(lam)

            p_under = normal_cdf(market_total, lam, sigma)
            p_over = 1.0 - p_under

            if lam > market_total:
                side = "OVER"
                p_selected = p_over
            elif lam < market_total:
                side = "UNDER"
                p_selected = p_under

        if p_selected is not None:
            fair_d = fair_decimal(p_selected)
            fair_a = decimal_to_american(fair_d)
            edge_pct = lookup_totals_juice(market_total, side)
            acc_d = acceptable_decimal(p_selected, edge_pct)
            acc_a = decimal_to_american(acc_d)

            results.append({
                "game_id": game_id,
                "date": row.get("date", ""),
                "time": row.get("time", ""),
                "team_1": team_1,
                "team_2": team_2,
                "market_total": market_total,
                "side": side,
                "model_probability": round(p_selected, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": fair_a,
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": acc_a,
                "league": "nba_ou",
            })

    # Save to CSV
    pd.DataFrame(results).to_csv(out_path, index=False)
    print(f"Created {out_path} using {len(results)} matched games.")

if __name__ == "__main__":
    main()
