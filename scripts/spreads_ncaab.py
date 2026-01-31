#!/usr/bin/env python3

import csv
from pathlib import Path
from statistics import NormalDist

# ============================================================
# CONFIGURATION
# ============================================================

DK_DIR = Path("docs/win/manual/normalized")
EDGE_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SIGMA = 7.2  # Standard deviation for NCAAB
EPS = 1e-9

# ============================================================
# MATH HELPERS
# ============================================================

def get_cover_prob(margin: float, spread: float, sigma: float) -> float:
    """Calculates probability to cover using Normal Distribution."""
    # z = (Predicted Margin + Spread) / Sigma
    # Note: Spread is usually negative for favorites (e.g., -8.5)
    z = (margin + spread) / sigma
    prob = NormalDist(mu=0, sigma=1).cdf(z)
    return max(EPS, min(1.0 - EPS, prob))

def american_to_decimal(a: float) -> float:
    if a > 0:
        return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)

# ============================================================
# MAIN
# ============================================================

def main():
    # Get latest files
    try:
        dk_file = sorted(DK_DIR.glob("norm_dk_ncaab_spreads_*.csv"))[-1]
        edge_file = sorted(EDGE_DIR.glob("edge_ncaab_*.csv"))[-1]
    except IndexError:
        print("Error: Required input files not found.")
        return

    # Extract date for filename
    parts = dk_file.stem.split("_")
    yyyy, mm, dd = parts[-3], parts[-2], parts[-1]
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{yyyy}_{mm}_{dd}.csv"

    # Load model points
    model = {}
    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            model[r["team"]] = {
                "points": float(r["points"]),
                "opponent": r["opponent"],
                "game_id": r["game_id"],
                "date": r["date"],
                "time": r["time"],
            }

    fields = [
        "game_id", "date", "time", "team", "opponent", "spread",
        "model_cover_prob", "dk_decimal_odds", "dk_american_odds",
        "market_prob", "edge_prob", "edge_pct", "league"
    ]

    processed_games = set()
    rows_written = 0

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fields)
        writer.writeheader()

        with dk_file.open(newline="", encoding="utf-8") as f_dk:
            reader = csv.DictReader(f_dk)
            
            # FLEXIBLE COLUMN DETECTION
            # Looks for 'odds' exactly, then 'american', then defaults to None
            odds_col = "odds" if "odds" in reader.fieldnames else \
                       next((c for c in reader.fieldnames if "american" in c.lower()), None)
            
            if not odds_col:
                print(f"Columns found: {reader.fieldnames}")
                raise RuntimeError("Could not find an 'odds' or 'american' column.")

            for r in reader:
                team = r["team"]
                if team not in model:
                    continue

                opp = model[team]["opponent"]
                game_id = model[team]["game_id"]

                # Ensure we only calculate each game once
                if game_id in processed_games:
                    continue

                spread = float(r["spread"])
                dk_american = float(r[odds_col])
                dk_decimal = american_to_decimal(dk_american)

                # Probabilities
                # Predicted Margin = Team Score - Opponent Score
                predicted_margin = model[team]["points"] - model[opp]["points"]
                cover_prob = get_cover_prob(predicted_margin, spread, SIGMA)
                
                market_prob = 1.0 / dk_decimal
                edge = cover_prob - market_prob

                writer.writerow({
                    "game_id": game_id,
                    "date": model[team]["date"],
                    "time": model[team]["time"],
                    "team": team,
                    "opponent": opp,
                    "spread": spread,
                    "model_cover_prob": round(cover_prob, 6),
                    "dk_decimal_odds": round(dk_decimal, 6),
                    "dk_american_odds": dk_american,
                    "market_prob": round(market_prob, 6),
                    "edge_prob": round(edge, 6),
                    "edge_pct": round(edge * 100.0, 2),
                    "league": "ncaab_spread",
                })
                
                processed_games.add(game_id)
                rows_written += 1

    print(f"Success: Wrote {rows_written} unique games to {out_path.name}")

if __name__ == "__main__":
    main()
