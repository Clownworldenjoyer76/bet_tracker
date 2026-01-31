import csv
import math
from pathlib import Path

# =========================
# CONFIG
# =========================

INPUT_PATH = Path(
    "docs/win/manual/normalized/norm_dk_ncaab_spreads_2026_01_31.csv"
)
JUICE_TABLE_PATH = Path(
    "config/ncaab/ncaab_spreads_juice_table.csv"
)
OUTPUT_PATH = Path(
    "docs/win/edge/edge_ncaab_spreads_2026_01_31.csv"
)

EPS = 1e-9


# =========================
# HELPERS
# =========================

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


def fair_decimal_from_prob(p):
    p = clamp_prob(p)
    return 1.0 / p


# =========================
# JUICE TABLE
# =========================

def load_spreads_juice_table(path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "market_type": r["market_type"].strip(),
                "band_low": float(r["band_low"]),
                "band_high": float(r["band_high"]),
                "side": r["side"].strip(),  # favorite / underdog / any
                "extra_juice_pct": float(r["extra_juice_pct"]),
            })
    return rows


def lookup_spread_juice(juice_table, spread_abs, side):
    for row in juice_table:
        if row["market_type"] != "spread":
            continue
        if not (row["band_low"] <= spread_abs <= row["band_high"]):
            continue
        if row["side"] not in ("any", side):
            continue
        return row["extra_juice_pct"]
    return 0.0


# =========================
# MAIN
# =========================

def main():
    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    output_rows = []

    with INPUT_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            spread = float(r["spread"])
            odds = float(r["odds"])

            side = "favorite" if spread < 0 else "underdog"
            spread_abs = abs(spread)

            # Market implied probability
            market_decimal = (
                float(r["decimal_odds"])
                if r["decimal_odds"]
                else american_to_decimal(odds)
            )
            market_prob = clamp_prob(1.0 / market_decimal)

            # Juice adjustment
            extra_juice = lookup_spread_juice(
                juice_table, spread_abs, side
            )

            adjusted_prob = clamp_prob(market_prob * (1.0 - extra_juice))

            fair_decimal = fair_decimal_from_prob(adjusted_prob)
            fair_american = decimal_to_american(fair_decimal)

            acceptable_decimal = fair_decimal
            acceptable_american = fair_american

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
                "acceptable_decimal_odds": round(acceptable_decimal, 6),
                "acceptable_american_odds": acceptable_american,
                "league": r["league"],
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(output_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    main()
