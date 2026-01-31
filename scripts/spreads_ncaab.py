import csv
import sys
from pathlib import Path

EPS = 1e-9


def american_to_decimal(odds):
    odds = float(odds)
    if odds > 0:
        return 1.0 + odds / 100.0
    return 1.0 + 100.0 / abs(odds)


def decimal_to_american(dec):
    dec = float(dec)
    if dec <= 1.0:
        return 0
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def clamp_prob(p):
    return max(EPS, min(1.0 - EPS, p))


def load_spreads_juice_table(path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "market_type": r["market_type"].strip(),
                "band_low": float(r["band_low"]),
                "band_high": float(r["band_high"]),
                "side": r["side"].strip(),
                "extra_juice_pct": float(r["extra_juice_pct"]),
            })
    return rows


def lookup_spread_juice(table, spread_abs, side):
    for row in table:
        if row["market_type"] != "spread":
            continue
        if not (row["band_low"] <= spread_abs <= row["band_high"]):
            continue
        if row["side"] not in ("any", side):
            continue
        return row["extra_juice_pct"]
    return 0.0


def main(run_date):
    input_path = Path(
        f"docs/win/manual/normalized/norm_dk_ncaab_spreads_{run_date}.csv"
    )
    output_path = Path(
        f"docs/win/edge/edge_ncaab_spreads_{run_date}.csv"
    )
    juice_path = Path(
        "config/ncaab/ncaab_spreads_juice_table.csv"
    )

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    juice_table = load_spreads_juice_table(juice_path)
    output_rows = []

    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            spread = float(r["spread"])
            odds = float(r["odds"])

            side = "favorite" if spread < 0 else "underdog"
            spread_abs = abs(spread)

            market_decimal = (
                float(r["decimal_odds"])
                if r["decimal_odds"]
                else american_to_decimal(odds)
            )

            market_prob = clamp_prob(1.0 / market_decimal)
            extra_juice = lookup_spread_juice(
                juice_table, spread_abs, side
            )

            adjusted_prob = clamp_prob(
                market_prob * (1.0 - extra_juice)
            )

            fair_decimal = 1.0 / adjusted_prob
            fair_american = decimal_to_american(fair_decimal)

            output_rows.append({
                "date": r["date"],
                "time": r["time"],
                "team": r["team"],
                "opponent": r["opponent"],
                "spread": spread,
                "market_decimal_odds": round(market_decimal, 6),
                "market_american_odds": int(odds),
                "fair_decimal_odds": round(fair_decimal, 6),
                "fair_american_odds": fair_american,
                "acceptable_decimal_odds": round(fair_decimal, 6),
                "acceptable_american_odds": fair_american,
                "league": r["league"],
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: spreads_ncaab.py YYYY_MM_DD")

    main(sys.argv[1])
