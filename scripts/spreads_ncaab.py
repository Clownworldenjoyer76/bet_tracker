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
REPORT_DIR = Path("docs/win/ncaab/report")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SIGMA = 7.2  
EDGE_THRESHOLD = 5.0  

# ============================================================
# MATH HELPERS
# ============================================================

def get_cover_prob(margin: float, spread: float, sigma: float) -> float:
    z = (margin + spread) / sigma
    prob = NormalDist(mu=0, sigma=1).cdf(z)
    return max(1e-9, min(1.0 - 1e-9, prob))

def american_to_decimal(a: float) -> float:
    if a > 0: return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)

def decimal_to_american(d: float) -> int:
    if d <= 1.0: return 0
    if d >= 2.0: return int((d - 1) * 100)
    return int(-100 / (d - 1))

# ============================================================
# MAIN
# ============================================================

def main():
    try:
        dk_file = sorted(DK_DIR.glob("norm_dk_ncaab_spreads_*.csv"))[-1]
        edge_file = sorted(EDGE_DIR.glob("edge_ncaab_*.csv"))[-1]
    except IndexError:
        print("Error: Required input files not found.")
        return

    parts = dk_file.stem.split("_")
    yyyy, mm, dd = parts[-3], parts[-2], parts[-1]
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{yyyy}_{mm}_{dd}.csv"
    report_path = REPORT_DIR / f"betting_report_{yyyy}_{mm}_{dd}.csv"

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

    # Internal processing fields
    fields = [
        "game_id", "date", "time", "team", "opponent", "spread",
        "model_cover_prob", "dk_decimal_odds", "dk_american_odds",
        "market_prob", "edge_prob", "edge_pct", "league"
    ]

    # Your specific Report Columns
    report_fields = [
        "Date", "Game / Team", "Win Probability", "Acceptable Line (American)",
        "Actual Line Taken (American)", "Edge (Actual - Acceptable)",
        "Stake ($)", "Result (Win/Loss)", "Payout ($)", "Net Profit ($)", "league"
    ]

    bet_report_rows = []
    processed_games = set()

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fields)
        writer.writeheader()

        with dk_file.open(newline="", encoding="utf-8") as f_dk:
            reader = csv.DictReader(f_dk)
            odds_col = "odds" if "odds" in reader.fieldnames else \
                       next((c for c in reader.fieldnames if "american" in c.lower()), None)

            for r in reader:
                team = r["team"]
                if team not in model: continue
                
                game_id = model[team]["game_id"]
                if game_id in processed_games: continue

                opp = model[team]["opponent"]
                spread = float(r["spread"])
                dk_american = float(r[odds_col])
                dk_decimal = american_to_decimal(dk_american)

                margin = model[team]["points"] - model[opp]["points"]
                prob = get_cover_prob(margin, spread, SIGMA)
                market_prob = 1.0 / dk_decimal
                edge_pct = (prob - market_prob) * 100.0

                # Data for full CSV
                row = {
                    "game_id": game_id, "date": model[team]["date"], "time": model[team]["time"],
                    "team": team, "opponent": opp, "spread": spread,
                    "model_cover_prob": round(prob, 4), "dk_decimal_odds": round(dk_decimal, 3),
                    "dk_american_odds": dk_american, "market_prob": round(market_prob, 4),
                    "edge_prob": round(prob - market_prob, 4), "edge_pct": round(edge_pct, 2),
                    "league": "ncaab_spread"
                }
                writer.writerow(row)
                processed_games.add(game_id)

                if edge_pct >= EDGE_THRESHOLD:
                    # Calculate Acceptable Line (Breakeven American Odds)
                    acceptable_decimal = 1.0 / prob
                    acceptable_american = decimal_to_american(acceptable_decimal)
                    
                    # Format for Betting Report
                    report_row = {
                        "Date": model[team]["date"],
                        "Game / Team": f"{team} ({spread}) vs {opp}",
                        "Win Probability": f"{round(prob * 100, 2)}%",
                        "Acceptable Line (American)": acceptable_american,
                        "Actual Line Taken (American)": "", # Blank for manual entry
                        "Edge (Actual - Acceptable)": "",   # Blank for manual entry
                        "Stake ($)": "",                   # Blank for manual entry
                        "Result (Win/Loss)": "",           # Blank for manual entry
                        "Payout ($)": "",                  # Blank for manual entry
                        "Net Profit ($)": "",              # Blank for manual entry
                        "league": ""                       # Blank as requested
                    }
                    bet_report_rows.append(report_row)

    # Write the high-value Betting Report CSV
    with report_path.open("w", newline="", encoding="utf-8") as f_rep:
        rep_writer = csv.DictWriter(f_rep, fieldnames=report_fields)
        rep_writer.writeheader()
        rep_writer.writerows(bet_report_rows)
    
    print(f"DONE: {len(bet_report_rows)} bets sent to report.")

if __name__ == "__main__":
    main()
