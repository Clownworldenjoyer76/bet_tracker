#!/usr/bin/env python3

import csv
import glob
from math import sqrt, erf
from pathlib import Path
from datetime import datetime
from collections import defaultdict

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nhl")
CONFIG_PATH = Path("config/nhl/nhl_juice_table.csv")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_totals_juice():
    rules = []
    with CONFIG_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["market_type"] != "totals":
                continue
            rules.append({
                "low": float(r["band_low"]),
                "high": float(r["band_high"]),
                "side": r["side"],
                "juice": float(r["extra_juice_pct"]),
            })
    return rules


TOTALS_RULES = load_totals_juice()


def lookup_totals_juice(total: float, side: str) -> float:
    for r in TOTALS_RULES:
        if r["low"] <= total <= r["high"]:
            if r["side"] == "any" or r["side"].lower() == side.lower():
                return r["juice"]
    return 0.0


def normal_cdf(x, mu, sigma):
    z = (x - mu) / (sigma * sqrt(2))
    return 0.5 * (1 + erf(z))


def decimal_to_american(d):
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def fair_decimal(p):
    return 1.0 / p


def main():
    files = sorted(glob.glob(str(INPUT_DIR / "edge_nhl_*.csv")))
    if not files:
        raise FileNotFoundError("No NHL edge files found")

    latest = files[-1]
    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_nhl_totals_{today:%Y_%m_%d}.csv"

    games = defaultdict(list)

    with open(latest, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("game_id"):
                games[r["game_id"]].append(r)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "game_id", "date", "time", "team_1", "team_2",
            "market_total", "side", "model_probability",
            "fair_decimal_odds", "fair_american_odds",
            "acceptable_decimal_odds", "acceptable_american_odds",
            "league"
        ])
        writer.writeheader()

        for gid, rows in games.items():
            r = rows[0]

            try:
                lam = float(r["total_points"])
                market = float(r["best_ou"])
            except Exception:
                continue

            sigma = sqrt(lam)
            p_under = normal_cdf(market, lam, sigma)
            p_over = 1.0 - p_under

            if lam > market:
                side = "OVER"
                p = p_over
            else:
                side = "UNDER"
                p = p_under

            fair_d = fair_decimal(p)
            fair_a = decimal_to_american(fair_d)

            juice = lookup_totals_juice(market, side)
            acc_d = fair_d * (1.0 + juice)
            acc_a = decimal_to_american(acc_d)

            writer.writerow({
                "game_id": gid,
                "date": r["date"],
                "time": r["time"],
                "team_1": r["team"],
                "team_2": r["opponent"],
                "market_total": market,
                "side": side,
                "model_probability": round(p, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": fair_a,
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": acc_a,
                "league": "nhl_ou",
            })

    print(f"Created {out_path}")


if __name__ == "__main__":
    main()
