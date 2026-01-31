#!/usr/bin/env python3

import csv
import glob
import os

SPREADS_GLOB = "docs/win/manual/normalized/norm_dk_ncaab_spreads_*.csv"
EDGE_GLOB = "docs/win/edge/edge_ncaab_*.csv"
JUICE_TABLE_PATH = "config/ncaab/ncaab_spreads_juice_table.csv"
OUTPUT_DIR = "docs/win/edge"


def extract_date(path: str) -> str:
    base = os.path.basename(path)
    parts = base.replace(".csv", "").split("_")
    return f"{parts[-3]}_{parts[-2]}_{parts[-1]}"


def american_from_decimal(d):
    if d <= 1:
        return 0
    if d < 2:
        return int(round(-100 / (d - 1)))
    return int(round((d - 1) * 100))


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_juice_table(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "band_low": float(r["band_low"]),
                "band_high": float(r["band_high"]),
                "side": r["side"],
                "extra_juice_pct": float(r["extra_juice_pct"]),
            })
    return rows


def lookup_extra_juice(table, spread_abs, side):
    for r in table:
        if r["band_low"] <= spread_abs <= r["band_high"]:
            if r["side"] == "any" or r["side"] == side:
                return r["extra_juice_pct"]
    return 0.0


def main():
    spreads_files = {extract_date(p): p for p in glob.glob(SPREADS_GLOB)}
    edge_files = {extract_date(p): p for p in glob.glob(EDGE_GLOB)}

    dates = sorted(set(spreads_files) & set(edge_files))
    if not dates:
        return

    juice_table = load_juice_table(JUICE_TABLE_PATH)

    for date in dates:
        spreads = load_csv(spreads_files[date])
        edge = load_csv(edge_files[date])

        edge_index = {}
        for e in edge:
            key = (
                e["date"],
                e["time"],
                e["team"],
                e["opponent"],
            )
            edge_index[key] = e

        out_rows = []

        for s in spreads:
            key = (
                s["date"],
                s["time"],
                s["team"],
                s["opponent"],
            )

            if key not in edge_index:
                continue

            e = edge_index[key]

            spread = float(s["spread"])
            spread_abs = abs(spread)
            side = "favorite" if spread < 0 else "underdog"

            model_p = float(e["win_probability"])
            fair_dec = 1.0 / model_p if model_p > 0 else 0.0

            extra_juice = lookup_extra_juice(juice_table, spread_abs, side)
            acceptable_dec = fair_dec * (1 + extra_juice)

            out_rows.append({
                "game_id": e["game_id"],
                "date": e["date"],
                "time": e["time"],
                "team": e["team"],
                "opponent": e["opponent"],
                "spread": spread,
                "model_probability": round(model_p, 6),
                "fair_decimal_odds": round(fair_dec, 6),
                "fair_american_odds": american_from_decimal(fair_dec),
                "acceptable_decimal_odds": round(acceptable_dec, 6),
                "acceptable_american_odds": american_from_decimal(acceptable_dec),
                "league": "ncaab_spread",
            })

        if not out_rows:
            continue

        out_path = os.path.join(
            OUTPUT_DIR,
            f"edge_ncaab_spreads_{date}.csv"
        )

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
            writer.writeheader()
            writer.writerows(out_rows)


if __name__ == "__main__":
    main()
