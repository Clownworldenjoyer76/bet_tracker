import csv
import glob
import math
import re
import sys
from pathlib import Path

BASE_SIGMA = 7.2
SIGMA_K = 0.25
SIGMA_MIN = 7.2
SIGMA_MAX = 12.5

SPREADS_GLOB = "docs/win/manual/normalized/norm_dk_ncaab_spreads_*.csv"
EDGE_GLOB = "docs/win/edge/edge_ncaab_*.csv"
JUICE_TABLE_PATH = "config/ncaab/ncaab_spreads_juice_table.csv"


def dynamic_sigma(spread):
    return min(SIGMA_MAX, max(SIGMA_MIN, BASE_SIGMA + SIGMA_K * abs(spread)))


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def decimal_to_american(d):
    if d <= 1:
        return 0
    if d < 2:
        return int(round(-100 / (d - 1)))
    return int(round(100 * (d - 1)))


def load_juice_table(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "market_type": r["market_type"],
                "band_low": float(r["band_low"]),
                "band_high": float(r["band_high"]),
                "side": r["side"],
                "extra_juice_pct": float(r["extra_juice_pct"]),
            })
    return rows


def juice_adjust(prob, spread, side, juice_rows):
    spread_abs = abs(spread)
    adj = 0.0
    for r in juice_rows:
        if r["market_type"] != "spread":
            continue
        if not (r["band_low"] <= spread_abs <= r["band_high"]):
            continue
        if r["side"] not in ("any", side):
            continue
        adj += r["extra_juice_pct"]
    return prob * (1.0 + adj)


def load_latest_file(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        raise RuntimeError(f"No files found for pattern: {pattern}")
    return files[-1]


def extract_date_from_filename(path):
    m = re.search(r"_(\d{4})_(\d{2})_(\d{2})\.csv$", path)
    if not m:
        raise RuntimeError(f"Could not extract date from filename: {path}")
    return f"{m.group(1)}_{m.group(2)}_{m.group(3)}"


def main():
    spreads_file = load_latest_file(SPREADS_GLOB)
    edge_file = load_latest_file(EDGE_GLOB)

    date_key = extract_date_from_filename(spreads_file)
    juice_rows = load_juice_table(JUICE_TABLE_PATH)

    model = {}
    with open(edge_file, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            model[(r["game_id"], r["team"])] = float(r["win_probability"])

    output_rows = []

    with open(spreads_file, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            game_id = r.get("game_id")
            if not game_id:
                continue

            team = r["team"]
            opponent = r["opponent"]
            spread = float(r["spread"])
            date = r["date"]
            time = r["time"]

            side = "favorite" if spread < 0 else "underdog"

            base_prob = model.get((game_id, team))
            if base_prob is None:
                continue

            sigma = dynamic_sigma(spread)
            z = spread / sigma
            model_prob = normal_cdf(z)
            model_prob = juice_adjust(model_prob, spread, side, juice_rows)

            fair_decimal = 1.0 / model_prob
            fair_american = decimal_to_american(fair_decimal)
            acceptable_decimal = fair_decimal * 1.12
            acceptable_american = decimal_to_american(acceptable_decimal)

            output_rows.append({
                "game_id": game_id,
                "date": date,
                "time": time,
                "team": team,
                "opponent": opponent,
                "spread": spread,
                "model_probability": round(model_prob, 6),
                "fair_decimal_odds": round(fair_decimal, 6),
                "fair_american_odds": fair_american,
                "acceptable_decimal_odds": round(acceptable_decimal, 6),
                "acceptable_american_odds": acceptable_american,
                "league": "ncaab_spread",
            })

    if not output_rows:
        raise RuntimeError(
            "spreads_ncaab.py produced ZERO rows — check game_id alignment "
            "between normalized spreads and edge input."
        )

    out_path = Path(f"docs/win/edge/edge_ncaab_spreads_{date_key}.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    main()
