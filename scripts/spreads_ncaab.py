#!/usr/bin/env python3

import csv
import math
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

EDGE_DIR = Path("docs/win/edge")
DK_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

# ============================================================
# CONSTANTS
# ============================================================

SIGMA = 7.2

# ============================================================
# HELPERS
# ============================================================

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def american_to_prob(a: float) -> float:
    if a < 0:
        return -a / (-a + 100.0)
    return 100.0 / (a + 100.0)

def load_spreads_juice_table(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "low": float(r["band_low"]),
                "high": float(r["band_high"]),
                "side": r["side"].lower(),
                "juice": float(r["extra_juice_pct"]),
            })
    return rows

def lookup_spreads_juice(table, spread_abs, side):
    for r in table:
        if r["low"] <= spread_abs <= r["high"]:
            if r["side"] == "any" or r["side"] == side:
                return r["juice"]
    return 0.0

# ============================================================
# MAIN
# ============================================================

def main():
    dk_file = sorted(DK_DIR.glob("norm_dk_ncaab_spreads_*.csv"))[-1]
    edge_file = sorted(EDGE_DIR.glob("edge_ncaab_*.csv"))[-1]

    date_part = dk_file.stem.split("_")[-3:]
    yyyy, mm, dd = date_part
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{yyyy}_{mm}_{dd}.csv"

    # ------------------------
    # load model points
    # ------------------------
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

    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    fields = [
        "game_id",
        "date",
        "time",
        "team",
        "opponent",
        "spread",
        "dk_american_odds",
        "model_probability",
        "dk_implied_probability",
        "edge",
        "league",
    ]

    rows_written = 0

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        with dk_file.open(newline="", encoding="utf-8") as dk:
            for r in csv.DictReader(dk):
                team = r["team"]
                if team not in model:
                    continue

                opp = model[team]["opponent"]
                if opp not in model:
                    continue

                spread = float(r["spread"])
                spread_abs = abs(spread)
                side = "favorite" if spread < 0 else "underdog"

                # CHANGE THIS LINE ONLY if column name differs
                dk_odds = float(r["american_odds"])

                team_pts = model[team]["points"]
                opp_pts = model[opp]["points"]
                margin = team_pts - opp_pts

                model_prob = normal_cdf((margin + spread) / SIGMA)

                dk_prob = american_to_prob(dk_odds)

                juice = lookup_spreads_juice(
                    juice_table,
                    spread_abs,
                    side
                )

                dk_prob_juiced = min(max(dk_prob + juice, 0.0), 1.0)

                edge = model_prob - dk_prob_juiced

                if edge <= 0:
                    continue

                w.writerow({
                    "game_id": model[team]["game_id"],
                    "date": model[team]["date"],
                    "time": model[team]["time"],
                    "team": team,
                    "opponent": opp,
                    "spread": spread,
                    "dk_american_odds": int(dk_odds),
                    "model_probability": round(model_prob, 6),
                    "dk_implied_probability": round(dk_prob_juiced, 6),
                    "edge": round(edge, 6),
                    "league": "ncaab_spread",
                })

                rows_written += 1

    if rows_written == 0:
        raise RuntimeError("No positive spread edges found.")

    print(f"Created {out_path} ({rows_written} edges)")

if __name__ == "__main__":
    main()
