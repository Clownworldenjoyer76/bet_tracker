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

def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))

def fair_decimal(p: float) -> float:
    return 1.0 / p

def acceptable_decimal(p: float, juice: float) -> float:
    return 1.0 / max(p - juice, 1e-9)

# ============================================================
# JUICE TABLE
# ============================================================

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

    # extract date from DK filename
    yyyy, mm, dd = dk_file.stem.split("_")[-3:]
    out_path = OUTPUT_DIR / f"edge_ncaab_spreads_{yyyy}_{mm}_{dd}.csv"

    # ------------------------
    # load edge model
    # ------------------------
    model_by_team = {}

    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            model_by_team[r["team"]] = {
                "game_id": r["game_id"],
                "date": r["date"],
                "time": r["time"],
                "opponent": r["opponent"],
                "points": float(r["points"]),
            }

    # ------------------------
    # load juice table
    # ------------------------
    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    rows_written = 0

    fields = [
        "game_id",
        "date",
        "time",
        "team",
        "opponent",
        "spread",
        "model_probability",
        "fair_decimal_odds",
        "fair_american_odds",
        "acceptable_decimal_odds",
        "acceptable_american_odds",
        "league",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        with dk_file.open(newline="", encoding="utf-8") as dk:
            for r in csv.DictReader(dk):
                team = r["team"]
                if team not in model_by_team:
                    continue

                meta = model_by_team[team]
                opp = meta["opponent"]

                if opp not in model_by_team:
                    continue

                spread = float(r["spread"])
                spread_abs = abs(spread)
                side = "favorite" if spread < 0 else "underdog"

                team_pts = meta["points"]
                opp_pts = model_by_team[opp]["points"]
                margin = team_pts - opp_pts

                # PATH A: pure model margin vs market spread
                cover_prob = normal_cdf((margin - spread) / SIGMA)

                juice = lookup_spreads_juice(
                    juice_table,
                    spread_abs,
                    side
                )

                fair_d = fair_decimal(cover_prob)
                acc_d = acceptable_decimal(cover_prob, juice)

                w.writerow({
                    "game_id": meta["game_id"],
                    "date": meta["date"],
                    "time": meta["time"],
                    "team": team,
                    "opponent": opp,
                    "spread": spread,
                    "model_probability": round(cover_prob, 6),
                    "fair_decimal_odds": round(fair_d, 6),
                    "fair_american_odds": decimal_to_american(fair_d),
                    "acceptable_decimal_odds": round(acc_d, 6),
                    "acceptable_american_odds": decimal_to_american(acc_d),
                    "league": "ncaab_spread",
                })

                rows_written += 1

    if rows_written == 0:
        raise RuntimeError(
            "spreads_ncaab.py produced ZERO rows — no DK teams matched edge model teams."
        )

    print(f"Created {out_path} ({rows_written} rows)")

if __name__ == "__main__":
    main()
