#!/usr/bin/env python3

import csv
import math
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

DK_DIR = Path("docs/win/manual/normalized")
EDGE_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# CONSTANTS
# ============================================================

SIGMA = 7.2
EPS = 1e-9

# ============================================================
# HELPERS
# ============================================================

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def american_to_decimal(a: float) -> float:
    if a > 0:
        return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)

def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

def clamp(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

# ============================================================
# MAIN
# ============================================================

def main():
    dk_file = sorted(DK_DIR.glob("norm_dk_ncaab_spreads_*.csv"))[-1]
    edge_file = sorted(EDGE_DIR.glob("edge_ncaab_*.csv"))[-1]

    parts = dk_file.stem.split("_")
    yyyy, mm, dd = parts[-3], parts[-2], parts[-1]

    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{yyyy}_{mm}_{dd}.csv"

    # ------------------------
    # load model (points only)
    # ------------------------
    model = {}

    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            team = r["team"]
            model[team] = {
                "points": float(r["points"]),
                "opponent": r["opponent"],
                "game_id": r["game_id"],
                "date": r["date"],
                "time": r["time"],
            }

    rows_written = 0

    fields = [
        "game_id",
        "date",
        "time",
        "team",
        "opponent",
        "spread",
        "model_cover_prob",
        "dk_decimal_odds",
        "dk_american_odds",
        "market_prob",
        "edge_prob",
        "edge_pct",
        "league",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fields)
        writer.writeheader()

        with dk_file.open(newline="", encoding="utf-8") as f_dk:
            reader = csv.DictReader(f_dk)

            # YOU SAID THE FILE HAS ODDS — WE USE THEM DIRECTLY
            odds_col = None
            for c in reader.fieldnames:
                if "american" in c.lower():
                    odds_col = c
                    break

            if odds_col is None:
                raise RuntimeError("No American odds column found in DK file")

            for r in reader:
                team = r["team"]

                if team not in model:
                    continue

                opp = model[team]["opponent"]
                if opp not in model:
                    continue

                spread = float(r["spread"])
                dk_american = float(r[odds_col])
                dk_decimal = american_to_decimal(dk_american)

                team_pts = model[team]["points"]
                opp_pts = model[opp]["points"]
                margin = team_pts - opp_pts

                cover_prob = clamp(
                    normal_cdf((margin + spread) / SIGMA)
                )

                market_prob = clamp(1.0 / dk_decimal)
                edge = cover_prob - market_prob

                writer.writerow({
                    "game_id": model[team]["game_id"],
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

                rows_written += 1

    if rows_written == 0:
        raise RuntimeError("ZERO rows written — team matching failed")

    print(f"Wrote {rows_written} rows to {out_path}")

if __name__ == "__main__":
    main()
