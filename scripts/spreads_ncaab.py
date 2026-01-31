import csv
import math
from pathlib import Path

# --------------------
# CONFIG
# --------------------
LEAGUE_STD = 7.2
MODEL_WEIGHT = 0.15
MARKET_WEIGHT = 0.85
EPS = 1e-6

INPUT_PATH = Path("docs/win/manual/cleaned")
OUTPUT_PATH = Path("docs/win/manual/processed")
JUICE_TABLE_PATH = Path("config/ncaab/ncaab_spreads_juice_table.csv")

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# --------------------
# MATH HELPERS
# --------------------
def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def clamp(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def decimal_to_american(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100 / (dec - 1.0)))

# --------------------
# JUICE TABLE
# --------------------
def load_spreads_juice_table(path: Path):
    table = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            table.append({
                "min_spread": float(r["min_spread"]),
                "max_spread": float(r["max_spread"]),
                "side": r["side"],
                "multiplier": float(r["multiplier"]),
            })
    return table

def lookup_multiplier(table, spread: float, side: str) -> float:
    s = abs(spread)
    for row in table:
        if row["side"] == side and row["min_spread"] <= s <= row["max_spread"]:
            return row["multiplier"]
    return 1.0

# --------------------
# CORE LOGIC
# --------------------
def cover_probability(model_margin: float, spread: float) -> float:
    effective_margin = (
        MODEL_WEIGHT * model_margin +
        MARKET_WEIGHT * spread
    )
    z = (effective_margin + spread) / LEAGUE_STD
    return clamp(normal_cdf(z))

# --------------------
# MAIN
# --------------------
def main():
    juice_table = load_spreads_juice_table(JUICE_TABLE_PATH)

    for csv_path in INPUT_PATH.glob("dk_ncaab_spread_*.csv"):
        rows = []

        with csv_path.open() as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        output_rows = []

        for r in rows:
            spread = float(r["spread"])
            model_margin = float(r["model_margin"])

            p_cover = cover_probability(model_margin, spread)
            p_other = 1.0 - p_cover

            side = "favorite" if spread < 0 else "underdog"
            opp_side = "underdog" if side == "favorite" else "favorite"

            mult = lookup_multiplier(juice_table, spread, side)
            opp_mult = lookup_multiplier(juice_table, spread, opp_side)

            fair_dec = 1.0 / p_cover
            fair_amer = decimal_to_american(fair_dec)

            acc_dec = 1.0 / clamp(p_cover * mult)
            acc_amer = decimal_to_american(acc_dec)

            output_rows.append({
                "game_id": r["game_id"],
                "date": r["date"],
                "time": r["time"],
                "team": r["team"],
                "opponent": r["opponent"],
                "spread": spread,
                "model_probability": round(p_cover, 6),
                "fair_decimal_odds": round(fair_dec, 6),
                "fair_american_odds": fair_amer,
                "acceptable_decimal_odds": round(acc_dec, 6),
                "acceptable_american_odds": acc_amer,
                "league": "ncaab_spread",
            })

            # opponent row
            opp_fair_dec = 1.0 / p_other
            opp_acc_dec = 1.0 / clamp(p_other * opp_mult)

            output_rows.append({
                "game_id": r["game_id"],
                "date": r["date"],
                "time": r["time"],
                "team": r["opponent"],
                "opponent": r["team"],
                "spread": -spread,
                "model_probability": round(p_other, 6),
                "fair_decimal_odds": round(opp_fair_dec, 6),
                "fair_american_odds": decimal_to_american(opp_fair_dec),
                "acceptable_decimal_odds": round(opp_acc_dec, 6),
                "acceptable_american_odds": decimal_to_american(opp_acc_dec),
                "league": "ncaab_spread",
            })

        out_file = OUTPUT_PATH / csv_path.name.replace("cleaned", "processed")
        with out_file.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
            writer.writeheader()
            writer.writerows(output_rows)

if __name__ == "__main__":
    main()
